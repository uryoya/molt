"""Molt Web API with Interface."""
import re
import redis
import docker
import subprocess
import os
import shlex
import requests
import sys
import argparse

from flask import Flask, Response, render_template, abort, request
from molt import Molt, MoltError

app = Flask(__name__)

# コマンドライン引数のパース
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', help='config file path')
args = parser.parse_args()

if args.config:
    cfg_file = args.config
else:
    cfg_file = 'config/molt_app.cfg'

if not os.path.exists(cfg_file):
    app.logger.error("{} が存在しません".format(cfg_file))
    sys.exit(1)

app.config.from_pyfile(cfg_file, silent=True)


molts = {}


@app.route('/<virtual_host>', strict_slashes=False)
def index(virtual_host):
    """Moltの実行をプレビューするページ."""
    try:
        rev, repo, user = virtual_host_parse(virtual_host)
    except Exception:
        abort(404)
    vhost = {'rev': rev, 'repo': repo, 'user': user, 'full': virtual_host}
    redirect_url = '//{}.{}/'.format(virtual_host, app.config['BASE_DOMAIN'])
    return render_template('index.html', vhost=vhost,
                           redirect_url=redirect_url)


@app.route('/molt/<virtual_host>', methods=['GET'], strict_slashes=False)
def molt(virtual_host):
    """Moltの実行をストリーミングする(Server-Sent Eventを使ったAPI)."""
    try:
        rev, repo, user = virtual_host_parse(virtual_host)
    except Exception:
        abort(404)

    print(molts)
    if virtual_host not in molts:
        molts[virtual_host] = Molt(rev, repo, user,
                                   app.config['BASE_DOMAIN'],
                                   app.config['GITHUB_USER'],
                                   app.config['GITHUB_TOKEN'])
        molts[virtual_host].start()

    def generate():
        """Dockerイメージ立ち上げ(ストリーミングするための関数).

        git clone から docker-compose upまでの一連の処理のSTDIOの送信と、Dockerイメージ
        の情報取得・設定をする
        """
        # コマンド群の実行
        try:
            yield event_stream_parser(':')
            out = ''
            while molts[virtual_host].p.is_alive() and out != '<<<molt-end>>>':
                out = molts[virtual_host].stdout.get()
                out = out.split('\r')
                data = out[-1]  # CRのみの行は保留されるので取り除く
                if data == '\n' and len(out) >= 2:
                    data = out[-2]  # CRLFを分割すると改行のみが取り出されてしまう
                re.sub(r'\x1B\[[0-9]{1,3}[mK]', '', data)
                yield event_stream_parser(data.strip())
            # RedisへIPアドレスとバーチャルホストの対応を書き込む
            r = redis.StrictRedis(host=app.config['REDIS_HOST'],
                                  port=app.config['REDIS_PORT'])
            r.hset('mirror-store', virtual_host,
                   molts[virtual_host].get_container_ip())
        except MoltError as e:
            yield event_stream_parser(e, event='failure')
        except Exception as e:
            print(e)
            yield event_stream_parser('Molt内部でエラーが発生しました。終了します...',
                                      event='failure')
        else:
            del molts[virtual_host]
            yield event_stream_parser('', event='success')
    return Response(generate(), mimetype='text/event-stream')


@app.route('/favicon.ico')
def favicon():
    """favicon.ico."""
    abort(404)


@app.template_filter('base_domain')
def base_domain_filter(path):
    """Staticファイルを呼び出す際のドメインを指定する."""
    return '//' + app.config['BASE_DOMAIN'] + ':' + str(app.config['PORT']) + \
        '/' + path


@app.route("/hook", methods=['POST'])
def hook():
    event = request.headers["X-GitHub-Event"]
    req = request.json
    if event != "pull_request":
        return "ok", 200
    elif req["action"] not in {"opened", "synchronize"}:
        return "ok", 200

    pr = req["pull_request"]
    pr_url = pr["comments_url"]
    pr_sha = pr["head"]["sha"][:7]
    pr_reponame = pr["head"]["repo"]["name"]
    pr_owner = pr["head"]["repo"]["owner"]["login"]

    payload = {
        "event": "COMMENT",
        "body": "Launched the preview environment!\nhttp://{}.{}.{}.{}\
        ".format(pr_sha, pr_reponame, pr_owner, app.config["BASE_DOMAIN"]),
    }
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": "token {}".format(app.config["GITHUB_TOKEN"]),
    }
    requests.post(
        pr_url,
        json=payload,
        headers=headers,
    )

    return "ok", 200


def virtual_host_parse(virtual_host):
    """Virtual_hostの文字列を 'rev', 'repo', 'user' に分割する.

    e.g.(1) "host.repo.sitory.user" => "host", "repo.sitory", "user"
    e.g.(2) "host.repository.user" => "host", "repository", "user"
    """
    p = re.compile(r'(?P<rev>^.+?)\.(?P<repo>.+)\.(?P<user>.+)$')
    m = p.search(virtual_host)
    return m.group('rev'), m.group('repo'), m.group('user')


def event_stream_parser(data, event=None, id=None, retry=None):
    """Server-Sent Event 形式へのパーサ."""
    if data == ':':  # SSEでコメントに相当する
        return ':\n\n'
    event_stream = ''
    if event:
        event_stream += 'event: {}\n'.format(event)
    event_stream += 'data: {}\n'.format(data)
    if id:
        event_stream += 'id: {}\n'.format(id)
    if retry:
        event_stream += 'retry: {}\n'.format(id)
    event_stream += '\n'
    return event_stream


if __name__ == '__main__':
    # RSA鍵の生成
    user = os.getenv('USER')
    ssh_key_path = os.path.expanduser("~")+"/.ssh/molt_deploy_key"
    if not os.path.exists(ssh_key_path):
        command = 'ssh-keygen -t rsa -N "" -f {}'.format(ssh_key_path)
        command = shlex.split(command)
        subprocess.Popen(command)

    # Dockerネットワークの作成
    clinet = docker.from_env()
    networks = clinet.networks.list()
    if 'molt-network' not in [network.name for network in networks]:
        command = 'docker network create --subnet=172.31.255.0/24 \
            --ip-range=172.31.255.0/24 --gateway=172.31.255.254 \
            -o "com.docker.network.bridge.host_binding_ipv4"="0.0.0.0" \
            molt-network'
        command = shlex.split(command)
        subprocess.Popen(command)

    app.run(host=app.config['HOST'], port=app.config['PORT'])
