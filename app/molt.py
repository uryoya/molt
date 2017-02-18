import re

from flask import Flask, Response
from molt_core import molt

app = Flask(__name__)


@app.route('/<virtual_host>', methods=['POST'])
def index(virtual_host):
    rev, repo, user = virtual_host_parse(virtual_host)

    def generate():     # For streaming
        for row in molt(rev, repo, user):
            yield row
    return Response(generate(), mimetype='text/text')


def virtual_host_parse(virtual_host):
    """ virtual_hostの文字列を 'rev', 'repo', 'user' に分割する
    e.g.(1) "host.repo.sitory.user" => "host", "repo.sitory", "user"
    e.g.(2) "host.repository.user" => "host", "repository", "user"
    """
    p = re.compile(r'(?P<rev>^.+?)\.(?P<repo>.+)\.(?P<user>.+)$')
    m = p.search(virtual_host)
    return m.group('rev'), m.group('repo'), m.group('user')


if __name__ == '__main__':
    app.run(debug=True)
