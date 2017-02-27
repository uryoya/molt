function moltUrl() {
    rev = document.getElementById('rev').id
    repo = document.getElementById('repo').id
    user = document.getElementById('user').id
    return {rev:rev, repo:repo, user:user}
}

console.log(moltUrl())
