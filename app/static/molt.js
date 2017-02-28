function moltUrl() {
    rev = document.getElementById('rev').innerHTML
    repo = document.getElementById('repo').innerHTML
    user = document.getElementById('user').innerHTML
    return `/molt/${rev}.${repo}.${user}`
}

function vhost() {
    rev = document.getElementById('rev').innerHTML
    repo = document.getElementById('repo').innerHTML
    user = document.getElementById('user').innerHTML
    return {rev: rev, repo: repo, user: user}
}

const evtSource = new EventSource(moltUrl());
evtSource.onmessage = function(e) {
    const newElement = document.createElement("p");
    newElement.className = 'console-row';
    newElement.innerHTML = e.data;
    document.getElementById('console').appendChild(newElement);
}
evtSource.onerror = function(e) {
    evtSource.close();
    vh = vhost();
    location.href = `http://${vh.rev}.${vh.repo}.${vh.user}.swkoubou.com/`
}
