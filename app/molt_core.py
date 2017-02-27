import pathlib
import glob
import re
import subprocess
import shlex


class Molt:
    def __init__(self, rev, repo, user):
        self.rev = rev
        self.repo = repo
        self.user = user
        self.repo_url = 'https://github.com/{}/{}.git/'.format(user, repo)
        self.repo_dir = str(pathlib.Path('./repos') / user / repo / rev)

    def molt(self):
        """ gitリポジトリのクローンと、Dockerイメージの立ち上げ """
        for command in (self._git_clone, self._git_checkout,
                        self._compose_build, self._compose_up):
            for row in command().stdout:
                yield row

    def get_molt_config(self):
        """ molt-config.yml ファイルからmoltの設定を読み込む
        e.g. molt-config.yml:
        MOLT: FILE: file1, file2, ...
        [EOF]
        """
        if 'molt-config.yml' in glob.glob(self.repo_dir):
            return []

        with open(self.repo_dir + '/molt-config.yml', 'r') as f:
            moltcfg = f.read()
        p = re.compile(r'^# MOLT: (?P<file>FILE: ?.+[ $]?)')    # FILE:要素の取得
        m = p.match(moltcfg)
        files = m.group('file')
        p = re.compile(r'^FILE: ?(?P<conf_files>.+[ $]?)')    # 要素の内容
        m = p.match(files)
        conf_files = m.group('conf_files')
        return conf_files.split(',')


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

    def _compose_build(self):
        conf = self.get_molt_config()
        if conf == []:
            command = 'docker-compose build --no-cache'
        else:
            expand_conf = '-f {} '*len(conf)
            expand_conf = expand_conf.format(*conf)
            command = 'docker-compose ' + expand_conf + 'build --no-cache'
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _compose_up(self):
        conf = self.get_molt_config()
        if conf == []:
            command = 'docker-compose up'
        else:
            expand_conf = '-f {} '*len(conf)
            expand_conf = expand_conf.format(*conf)
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
