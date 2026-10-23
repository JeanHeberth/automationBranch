from services import repo_snapshot
from services.git_runner import GitServiceError
from services.repo_snapshot import collect_repo_snapshot


def test_snapshot_descobre_branch_atual_e_coleta_tudo(git_repo):
    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.branch == "main"
    assert snapshot.local_branches == ["main"]
    assert snapshot.remote_branches == []
    assert snapshot.remotes == []
    assert [row["subject"] for row in snapshot.commit_rows] == ["primeiro commit"]
    assert snapshot.changed_files == {"staged": [], "unstaged": []}
    assert snapshot.commit_error is None and snapshot.changed_files_error is None


def test_snapshot_usa_branch_informada_sem_consultar(git_repo, monkeypatch):
    def nao_deveria_chamar(_repo):
        raise AssertionError("get_current_branch não deveria ser chamado")

    monkeypatch.setattr(repo_snapshot, "get_current_branch", nao_deveria_chamar)

    assert collect_repo_snapshot(git_repo, "main").branch == "main"


def test_snapshot_reporta_arquivos_alterados(git_repo):
    import pathlib

    pathlib.Path(git_repo, "novo.txt").write_text("x", encoding="utf-8")

    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.changed_files["unstaged"] == ["? | novo.txt"]


def test_snapshot_erro_de_commits_vira_texto(git_repo, monkeypatch):
    def falha(*a, **k):
        raise GitServiceError("log quebrou")

    monkeypatch.setattr(repo_snapshot, "get_recent_commit_rows", falha)

    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.commit_error == "log quebrou"
    assert snapshot.commit_rows == []
    assert snapshot.local_branches == ["main"]


def test_snapshot_erro_de_branches_propaga(git_repo, monkeypatch):
    def falha(*a, **k):
        raise GitServiceError("sem repo")

    monkeypatch.setattr(repo_snapshot, "get_local_and_remote_branches", falha)

    import pytest

    with pytest.raises(GitServiceError, match="sem repo"):
        collect_repo_snapshot(git_repo)
