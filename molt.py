import re

from flask import Flask

app = Flask(__name__)


@app.route('/<virtual_host>', methods=['POST'])
def index(virtual_host):
    # e.g. "host.repo.sitory.user" => "host", "repo.sitory", "user"
    # e.g.2 "host.repository.user" => "host", "repository", "user"
    p = re.compile(r'(?P<rev>^.+?)\.(?P<repo>.+)\.(?P<user>.+)$')
    m = p.search(virtual_host)
    rev = m.group('rev')
    repo = m.group('repo')
    user = m.group('user')
    return "REV:{} REPO:{} USER:{}".format(rev, repo, user)


if __name__ == '__main__':
    app.run(debug=True)
