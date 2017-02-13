import pathlib
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
        for command in (self._git_clone, self._git_checkout):
            for row in command().stdout:
                yield row

    def _git_clone(self):
        command = 'git clone --progress {} {}'.format(
            self.repo_url, self.repo_dir)
        return subprocess.Popen(shlex.split(command),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    def _git_checkout(self):
        command = 'git checkout {}'.format(self.rev)
        return subprocess.Popen(shlex.split(command),
                                cwd=self.repo_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)


if __name__ == '__main__':
    rev = '32b5b45'
    repo = 'molt'
    user = 'swkoubou'

    m = Molt(rev, repo, user)
    for line in m.molt():
        print(line.decode(), end='', flush=True)
