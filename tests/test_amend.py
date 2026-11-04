import subprocess

import pytest

from services.commit_service import amend_commit, is_last_commit_pushed
from services.git_runner import GitServiceError
from services.sync_service import git_push_force_with_lease


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "feature/x", str(work)], check=True)
    _git(work, "config", "user.email", "t@t.com")
    _git(work, "config", "user.name", "T")
    _git(work, "remote", "add", "origin", str(remote))
    (work / "a.txt").write_text("1")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "primeiro")
    return str(work)


def test_amend_sem_mensagem_mantem_mensagem_e_inclui_arquivos(repo):
    (open(f"{repo}/b.txt", "w")).write("2")
    amend_commit(repo)
    assert _git(repo, "log", "-1", "--format=%s") == "primeiro"
    assert "b.txt" in _git(repo, "show", "--name-only", "--format=")
    assert _git(repo, "rev-list", "--count", "HEAD") == "1"


def test_amend_com_mensagem_troca_mensagem(repo):
    amend_commit(repo, "  nova mensagem  ")
    assert _git(repo, "log", "-1", "--format=%s") == "nova mensagem"


def test_amend_sem_commits_falha(tmp_path):
    vazio = tmp_path / "vazio"
    subprocess.run(["git", "init", "-q", str(vazio)], check=True)
    with pytest.raises(GitServiceError):
        amend_commit(str(vazio))


def test_commit_nao_enviado_sem_upstream(repo):
    assert is_last_commit_pushed(repo, "feature/x") is False


def test_fluxo_push_amend_force_with_lease(repo):
    _git(repo, "push", "-q", "-u", "origin", "feature/x")
    assert is_last_commit_pushed(repo, "feature/x") is True

    amend_commit(repo, "reescrito")
    assert is_last_commit_pushed(repo, "feature/x") is False

    git_push_force_with_lease(repo)
    assert _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "@{u}")


def test_amend_com_paths_inclui_so_selecionados(repo):
    (open(f"{repo}/b.txt", "w")).write("2")
    (open(f"{repo}/c.txt", "w")).write("3")
    _git(repo, "add", "c.txt")

    amend_commit(repo, None, ["b.txt"])

    files = _git(repo, "show", "--name-only", "--format=").splitlines()
    assert "b.txt" in files and "c.txt" not in files
    assert _git(repo, "diff", "--cached", "--name-only") == "c.txt"
    assert _git(repo, "log", "-1", "--format=%s") == "primeiro"


def test_amend_com_lista_vazia_altera_so_mensagem(repo):
    (open(f"{repo}/b.txt", "w")).write("2")
    _git(repo, "add", "b.txt")

    amend_commit(repo, "nova", [])

    assert _git(repo, "log", "-1", "--format=%s") == "nova"
    assert "b.txt" not in _git(repo, "show", "--name-only", "--format=")
    assert _git(repo, "diff", "--cached", "--name-only") == "b.txt"


def test_amend_lista_vazia_sem_mensagem_falha(repo):
    with pytest.raises(GitServiceError):
        amend_commit(repo, None, [])
