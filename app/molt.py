"""Molt Web API with Interface."""
import re
import redis

from flask import Flask, Response, render_template, abort
from molt_core import Molt

app = Flask(__name__)


@app.route('/<virtual_host>')
def index(virtual_host):
    """Moltの実行をプレビューするページ."""
    rev, repo, user = virtual_host_parse(virtual_host)
    vhost = {'rev': rev, 'repo': repo, 'user': user}
    return render_template('index.html', vhost=vhost)


@app.route('/molt/<virtual_host>', methods=['GET'])
def molt(virtual_host):
    """Moltの実行をストリーミングする(Server-Sent Eventを使ったAPI)."""
    rev, repo, user = virtual_host_parse(virtual_host)
    m = Molt(rev, repo, user)
    r = redis.StrictRedis()

    def generate(m, r):
        """Dockerイメージ立ち上げ(ストリーミングするための関数).

        git clone から docker-compose upまでの一連の処理のSTDIOの送信と、Dockerイメージ
        の情報取得・設定をする
        """
        # コマンド群の実行
        for row in m.molt():
            row = row.decode()
            data = row.split('\r')[-1]    # CRのみの行は保留されるので取り除く
            print(data)
            yield event_stream_parser(data)
        # RedisへIPアドレスとバーチャルホストの対応を書き込む
        r.hset('mirror-store', virtual_host, m.get_container_ip())
    return Response(generate(m, r), mimetype='text/event-stream')


@app.route('/favicon.ico')
def favicon():
    """favicon.ico."""
    abort(404)


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
    app.run(host='0.0.0.0')
