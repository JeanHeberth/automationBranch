import pytest

from services import branch_service
from services.branch_service import (
    create_branch,
    get_current_branch,
    get_local_branches,
    get_remote_branches,
    is_detached_head,
    is_git_repository,
)
from services.git_runner import run_git_command


def test_is_git_repository(git_repo, tmp_path):
    assert is_git_repository(git_repo) is True
    nao_repo = tmp_path / "vazio"
    nao_repo.mkdir()
    assert is_git_repository(str(nao_repo)) is False


def test_get_current_branch(git_repo):
    assert get_current_branch(git_repo) == "main"
    assert is_detached_head(git_repo) is False


def test_get_current_branch_detached_head(git_repo):
    sha = run_git_command(git_repo, ["rev-parse", "HEAD"])
    run_git_command(git_repo, ["checkout", sha])

    assert is_detached_head(git_repo) is True

    atual = get_current_branch(git_repo)
    assert atual  # não pode ser vazio
    assert sha.startswith(atual)  # é o hash abreviado


def test_get_local_branches(git_repo):
    assert get_local_branches(git_repo) == ["main"]


def test_get_remote_branches_filtra_ponteiro_e_origin(monkeypatch):
    saida = "origin\norigin/HEAD -> origin/main\norigin/main\norigin/feature/x\n"
    monkeypatch.setattr(branch_service, "run_git_command", lambda *a, **k: saida)

    assert get_remote_branches("/repo") == ["origin/main", "origin/feature/x"]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("minha feature", "feature/minha-feature"),
        ("bugfix/login", "bugfix/login"),
        ("Hotfix/Prod", "hotfix/prod"),
        ("release/1.0", "release/1.0"),
    ],
)
def test_create_branch_normaliza_nome(monkeypatch, entrada, esperado):
    capturado = {}

    def fake(repo_path, args, *a, **k):
        capturado["args"] = args
        return ""

    monkeypatch.setattr(branch_service, "run_git_command", fake)

    create_branch("/repo", entrada)

    assert capturado["args"] == ["checkout", "-b", esperado]


def test_create_branch_nome_vazio(monkeypatch):
    monkeypatch.setattr(branch_service, "run_git_command", lambda *a, **k: "")
    with pytest.raises(ValueError):
        create_branch("/repo", "   ")
