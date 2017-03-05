"""Molt Core Interfaces."""
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
        self.repo_url = 'https://github.com/{}/{}.git/'.format(user, repo)
        self.repo_dir = str(Path('./repos') / user / repo / rev)
        self.molt_yml_fp = None

    def __del__(self):
        """デストラクタ."""
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
        container = client.containers.get('container name')
        return container.attrs['NetworkSettings']['IPAddress']

    def gen_container_name(self):
        """docker-compose.ymlで使用するcontainer_nameを生成する."""
        molt_conf = self.get_molt_config_files()
        return '-'.join([self.user, self.repo, self.rev, molt_conf['entry']])

    def get_molt_config_files(self):
        """molt-config.yml ファイルからmoltの設定を読み込む.

        e.g. molt-config.yml:
        MOLT: FILE: file1 file2 ... ENTRY: entryname
        [EOF]
        """
        with open(self.repo_dir + '/molt-config.yml', 'r') as f:
            s = f.read()
        moltcfg = s.split()
        files = moltcfg[moltcfg.index('FILE:') + 1:moltcfg.index('ENTRY:')]
        entry = moltcfg[moltcfg.index('ENTRY:') + 1:][0]
        return {'file': files, 'entry': entry}

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
        compose_files = molt_conf['file']
        data = {}
        for filename in compose_files:
            with open(str(Path(self.repo_dir) / filename), 'r') as f:
                data.update(yaml.load(f))    # 各yamlファイルを統合・上書き
        molt_conf = self.get_molt_config_files()
        # container_nameの追加
        data['services']['web']['container_name'] = self.gen_container_name()
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
        compose_files = molt_conf['file']
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
        compose_files = molt_conf['file']
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


if __name__ == '__main__':
    rev = '4809f18'
    repo = 'molt-test'
    user = 'swkoubou'

    m = Molt(rev, repo, user)
    for line in m.molt():
        print(line.decode(), end='', flush=True)
    print()
