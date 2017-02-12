import subprocess
import shlex


def molt(rev, repo, user):
    """ gitリポジトリのクローンと、Dockerイメージの立ち上げ """
    command = 'git clone --progress {} ./tmp'.format(   # コマンドの生成
        git_ripository_url(repo, user))
    args = shlex.split(command)     # コマンドをリストに分解
    popen = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    return popen.stdout


def git_ripository_url(repo, user):
    return 'https://github.com/{}/{}.git'.format(user, repo)


if __name__ == '__main__':
    rev = '32b5b45cf39f2f49f340b664a85522059bc4fe0a'
    repo = 'molt'
    user = 'swkoubou'

    for line in molt(rev, repo, user):
        print(line.decode(), end='', flush=True)
