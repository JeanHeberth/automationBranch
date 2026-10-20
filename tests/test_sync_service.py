import pytest

from services import sync_service
from services.git_runner import GitServiceError


def _captura(capturado):
    def fake(repo, args, **k):
        capturado["args"] = args
        return "ok"

    return fake


def test_git_pull_com_upstream_faz_pull_simples(monkeypatch):
    capturado = {}
    monkeypatch.setattr(sync_service, "get_current_branch", lambda repo: "main")
    monkeypatch.setattr(sync_service, "has_upstream", lambda repo, branch: True)
    monkeypatch.setattr(sync_service, "run_git_command", _captura(capturado))

    assert sync_service.git_pull("/repo") == "ok"
    assert capturado["args"] == ["pull"]


def test_git_pull_sem_upstream_sem_origin(monkeypatch):
    monkeypatch.setattr(sync_service, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(sync_service, "has_upstream", lambda repo, branch: False)
    monkeypatch.setattr(sync_service, "get_remotes", lambda repo: [])

    with pytest.raises(GitServiceError, match="origin"):
        sync_service.git_pull("/repo")


def test_git_pull_sem_upstream_branch_inexistente_no_remoto(monkeypatch):
    monkeypatch.setattr(sync_service, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(sync_service, "has_upstream", lambda repo, branch: False)
    monkeypatch.setattr(sync_service, "get_remotes", lambda repo: ["origin"])
    monkeypatch.setattr(sync_service, "run_git_command", lambda repo, args, **k: "")

    with pytest.raises(GitServiceError, match="push primeiro"):
        sync_service.git_pull("/repo")


def test_git_push_sem_upstream_define_upstream(monkeypatch):
    capturado = {}
    monkeypatch.setattr(sync_service, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(sync_service, "has_upstream", lambda repo, branch: False)
    monkeypatch.setattr(sync_service, "run_git_command", _captura(capturado))

    sync_service.git_push("/repo")
    assert capturado["args"] == ["push", "--set-upstream", "origin", "feature/x"]
