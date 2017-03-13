"""Molt Core Interfaces."""
import os
import subprocess
import shlex
import docker
import yaml
import tempfile
import uuid

from pathlib import Path


class Molt:
    """指定されたvirtual_hostを元にDockerイメージの立ち上げ・管理をする."""

    def __init__(self, rev, repo, user, base_domain):
        """コンストラクタ."""
        self.rev = rev
        self.repo = repo
        self.user = user
        self.molt_domain = '{}.{}.{}.{}'.format(rev, repo, user, base_domain)
        self.repo_url = 'git@github.com:{}/{}.git'.format(user, repo)
        self.repo_dir = str(Path('./repos') / user / repo / rev)
        self.molt_yml_fp = None
        self.config = None

    def __del__(self):
        """デストラクタ."""
        if self.molt_yml_fp:
            self.molt_yml_fp.close()

    def molt(self):
        """Gitリポジトリのクローンと、Dockerイメージの立ち上げ."""
        # リポジトリのcloneかpull
        if os.path.exists(self.repo_dir):
            proc = self._git_pull()
        else:
            proc = self._git_clone()
        for row in proc.stdout:
            yield row
        proc.wait()
        # 特定コミットへのcheckout
        proc = self._git_checkout()
        for row in proc.stdout:
            yield row
        proc.wait()
        # Molt固有設定の読み込み
        self.config = self.get_molt_config_files()
        # 初期化処理の実行
        if 'init' in self.config.keys():
            proc = self._init_repository()
            for row in proc.stdout:
                yield row
            proc.wait()
        # composeファイルの統合
        proc = self._marge_docker_compose()
        for row in proc.stdout:
            yield row
        proc.wait()
        # docker-compose build
        proc = self._compose_build()
        for row in proc.stdout:
            yield row
        proc.wait()
        # docker-compose up
        proc = self._compose_up()
        for row in proc.stdout:
            yield row
        proc.wait()

    def get_container_ip(self):
        """Moltで生成したコンテナのIPアドレスを取得する."""
        client = docker.from_env()
        container = client.containers.get(
                self.gen_container_name(self.config['entry']))
        key = list(container.attrs['NetworkSettings']['Networks'].keys())[0]
        return container.attrs['NetworkSettings']['Networks'][key]['IPAddress']

    def gen_container_name(self, service_name):
        """docker-compose.ymlで使用するcontainer_nameを生成する."""
        return '-'.join([self.user, self.repo, self.rev, service_name])

    def get_molt_config_files(self):
        """molt-config.yml ファイルからmoltの設定を読み込む.

        e.g. molt-config.yml:
        compose_files:
          - docker-compose.1.yaml
          - docker-compose.2.yaml
        entry: entry_service_name
        """
        if not os.path.exists(self.repo_dir + '/molt-config.yml'):
            raise MoltError('molt-config.ymlがリポジトリに存在しません.')
        with open(self.repo_dir + '/molt-config.yml', 'r') as f:
            molt_conf = yaml.load(f)
        if not molt_conf:
            raise MoltError('molt-config.yml内の設定が見つかりません')
        if 'compose_files' not in molt_conf.keys():
            raise MoltError('"compose_files"の設定が必要ですが、このリポジトリの\
                            molt-config.ymlには存在しません.')
        if 'entry' not in molt_conf.keys():
            raise MoltError('"entry"の設定が必要ですが、このリポジトリの\
                            molt-config.ymlには存在しません.')
        return molt_conf

    # 以下はSHELLで実行するコマンドの記述
    def _git_clone(self):
        wd = os.getcwd()
        command = 'git clone --progress {} {}'.format(self.repo_url,
                                                      self.repo_dir)
        return subprocess.Popen(shlex.split(command),
                                env={
                                'GIT_SSH': '{}/scripts/git-ssh.sh'.format(wd)
                                },
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _git_pull(self):
        wd = os.getcwd()
        command = 'git pull --progress'
        return subprocess.Popen(shlex.split(command),
                                env={
                                'GIT_SSH': '{}/scripts/git-ssh.sh'.format(wd)
                                },
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _git_checkout(self):
        command = 'git checkout {}'.format(self.rev)
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _init_repository(self):
        if os.path.isfile(self.config['init']):
            command = 'bash {}'.format(self.config['init'])
        else:
            tag = uuid.uuid4().hex[:7]
            filename = '/tmp/__mot_config_file{}'.format(tag)
            with open(filename, 'w') as f:
                f.write(self.config['init'])
            command = 'bash {}'.format(filename)
        return subprocess.Popen(shlex.split(command),
                                env={
                                'MOLT_DOMAIN': self.molt_domain
                                },
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _marge_docker_compose(self):
        """Molt用にdocker-compose.ymlを統合して書き換える."""
        compose_files = self.config['compose_files']
        data = {}

        for filename in compose_files:
            with open(str(Path(self.repo_dir) / filename), 'r') as f:
                data.update(yaml.load(f))    # 各yamlファイルを統合・上書き

        # molt 接続用のネットワークを追加
        if 'networks' in data:
            data['networks'].update({
                    'molt-network': {'external': {'name': 'molt-network'}}
                    })
        else:
            data['networks'] = {
                    'molt-network': {'external': {'name': 'molt-network'}}
                    }

        # 各serviceにcontainer_name, networkを追加, portsを削除
        for s_name, s_conf in data['services'].items():
            s_conf['container_name'] = self.gen_container_name(s_name)
            if 'networks' in s_conf:
                s_conf['networks'].append('molt-network')
            else:
                s_conf['networks'] = ['molt-network']
            if 'ports' in s_conf:
                del s_conf['ports']

        # 変更したcompose fileの書き出し
        fp = tempfile.NamedTemporaryFile(mode='w')
        yaml.dump(data, fp)
        self.molt_yml_fp = fp

        # メソッドの形式を同じにするためにsubprocessを使用
        command = 'echo "moltの設定ファイルを生成中..."'
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _compose_build(self):
        compose_files = self.config['compose_files']
        if compose_files == []:
            command = 'docker-compose build --no-cache'
        else:
            compose_files.append(self.molt_yml_fp.name)
            expand_conf = '-f {} '*len(compose_files)
            expand_conf = expand_conf.format(*compose_files)
            command = 'docker-compose ' + expand_conf + 'build --no-cache'
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _compose_up(self):
        compose_files = self.config['compose_files']
        if compose_files == []:
            command = 'docker-compose up -d'
        else:
            compose_files.append(self.molt_yml_fp.name)
            expand_conf = '-f {} '*len(compose_files)
            expand_conf = expand_conf.format(*compose_files)
            command = 'docker-compose ' + expand_conf + 'up -d'
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class MoltError(Error):
    """Exception raised for errors in molting."""

    def __init__(self, message):
        self.message = message


# test
if __name__ == '__main__':
    rev = '0af08d4'
    repo = 'molt-test'
    user = 'swkoubou'

    m = Molt(rev, repo, user)
    try:
        for line in m.molt():
            print(line.decode(), end='', flush=True)
    except MoltError as e:
        print(e.message)
    print()
