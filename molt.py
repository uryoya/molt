"""Molt Core Interfaces."""
import os
import subprocess
import shlex
import docker
import yaml
import tempfile

from pathlib import Path


class Molt:
    """指定されたvirtual_hostを元にDockerイメージの立ち上げ・管理をする."""

    def __init__(self, rev, repo, user):
        """コンストラクタ."""
        self.rev = rev
        self.repo = repo
        self.user = user
        self.repo_url = 'git@github.com:{}/{}.git'.format(user, repo)
        self.repo_dir = str(Path('./repos') / user / repo / rev)
        self.molt_yml_fp = None

    def __del__(self):
        """デストラクタ."""
        if self.molt_yml_fp:
            self.molt_yml_fp.close()

    def molt(self):
        """Gitリポジトリのクローンと、Dockerイメージの立ち上げ."""
        for command in (self._git_clone, self._git_checkout,
                        self._marge_docker_compose,
                        self._compose_build, self._compose_up):
            for row in command().stdout:
                yield row

    def get_container_ip(self):
        """Moltで生成したコンテナのIPアドレスを取得する."""
        client = docker.from_env()
        molt_conf = self.get_molt_config_files()
        container = client.containers.get(
                self.gen_container_name(molt_conf['entry']))
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
        if not molt_conf:   # is None
            raise MoltError('molt-config.yml内に設定が存在しません.')
        if 'compose_files' not in molt_conf.keys():
            raise MoltError('"compose_files"の設定が必要ですが、このリポジトリの\
                            molt-config.ymlには存在しません.')
        if 'entry' not in molt_conf.keys():
            raise MoltError('"entry"の設定が必要ですが、このリポジトリの\
                            molt-config.ymlには存在しません.')
        files = molt_conf['compose_files']
        entry = molt_conf['entry']
        return {'files': files, 'entry': entry}

    # 以下はSHELLで実行するコマンドの記述
    def _git_clone(self):
        command = 'git clone --progress {} {}'.format(self.repo_url,
                                                      self.repo_dir)
        return subprocess.Popen(shlex.split(command),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _git_checkout(self):
        command = 'git checkout {}'.format(self.rev)
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _marge_docker_compose(self):
        """Molt用にdocker-compose.ymlを統合して書き換える."""
        molt_conf = self.get_molt_config_files()
        compose_files = molt_conf['files']
        data = {}
        for filename in compose_files:
            with open(str(Path(self.repo_dir) / filename), 'r') as f:
                data.update(yaml.load(f))    # 各yamlファイルを統合・上書き
        # container_nameの追加
        for s_name, s_conf in data['services'].items():
            s_conf['container_name'] = self.gen_container_name(s_name)
        data['networks'] = {'default': {'external': {'name': 'molt-network'}}}
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
        molt_conf = self.get_molt_config_files()
        compose_files = molt_conf['files']
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
        molt_conf = self.get_molt_config_files()
        compose_files = molt_conf['files']
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
