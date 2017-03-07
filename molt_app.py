"""Molt Web API with Interface."""
import re
import redis
import docker
import subprocess
import os
import shlex
import requests

from flask import Flask, render_template, abort, request
from flask_socketio import SocketIO, emit, disconnect
from molt import Molt

app = Flask(__name__)
app.config.from_pyfile('config/molt_app.cfg', silent=True)
socketio = SocketIO(app)


@app.route('/<virtual_host>')
def index(virtual_host):
    """Moltの実行をプレビューするページ."""
    rev, repo, user = virtual_host_parse(virtual_host)
    vhost = {'rev': rev, 'repo': repo, 'user': user, 'full': virtual_host}
    redirect_url = '//{}.{}/'.format(virtual_host, app.config['BASE_DOMAIN'])
    return render_template('index.html', vhost=vhost,
                           redirect_url=redirect_url)


@socketio.on('molt')
def handle_molt(virtual_host):
    """Moltの実行をストリーミングする(WebSocketを使ったAPI)."""
    print(virtual_host)
    m = Molt(virtual_host['rev'], virtual_host['repo'], virtual_host['user'])
    r = redis.StrictRedis(host=app.config['REDIS_HOST'],
                          port=app.config['REDIS_PORT'])
    # コマンド群の実行と経過の送信
    for row in m.molt():
        row = row.decode()
        data = row.split('\r')[-1]    # CRのみの行は保留されるので取り除く
        emit('stdio', {'data': data})
    # RedisへIPアドレスとバーチャルホストの対応を書き込む
    r.hset('mirror-store', virtual_host, m.get_container_ip())
    disconnect()


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
        command = 'docker network create --subnet=172.28.0.0/16 \
            --ip-range=172.28.0.0/24 --gateway=172.28.0.254 \
            -o "com.docker.network.bridge.host_binding_ipv4"="0.0.0.0" \
            molt-network'
        command = shlex.split(command)
        subprocess.Popen(command)

    socketio.run(app, host=app.config['HOST'], port=app.config['PORT'])
