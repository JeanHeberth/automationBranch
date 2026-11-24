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


def test_snapshot_sem_branch_busca_log_de_head_em_paralelo(git_repo, monkeypatch):
    # O log não espera o for-each-ref descobrir o nome da branch: usa HEAD direto.
    revisoes = []
    original = repo_snapshot.get_recent_commit_rows

    def espia(repo, revisao, limite):
        revisoes.append(revisao)
        return original(repo, revisao, limite)

    monkeypatch.setattr(repo_snapshot, "get_recent_commit_rows", espia)

    snapshot = collect_repo_snapshot(git_repo)

    assert revisoes == ["HEAD"]
    assert snapshot.branch == "main"
    assert [row["subject"] for row in snapshot.commit_rows] == ["primeiro commit"]


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

    monkeypatch.setattr(repo_snapshot, "get_branch_overview", falha)

    import pytest

    with pytest.raises(GitServiceError, match="sem repo"):
        collect_repo_snapshot(git_repo)


def test_snapshot_usa_poucos_processos_git(git_repo, monkeypatch):
    import subprocess

    comandos = []
    original = subprocess.run

    def conta(cmd, *a, **k):
        comandos.append(cmd[3:5])
        return original(cmd, *a, **k)

    monkeypatch.setattr("services.git_runner.subprocess.run", conta)

    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.branch == "main"
    # for-each-ref (branches + remotes + atual), status, log, stash list — mais `git remote`
    # porque este repositório não tem nenhum remote buscado.
    assert sorted(c[0] for c in comandos) == sorted(["for-each-ref", "-c", "log", "stash", "remote"])


def test_snapshot_com_remote_buscado_dispensa_git_remote(git_repo, monkeypatch):
    import subprocess

    subprocess.run(["git", "-C", git_repo, "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    chamadas = []
    original = repo_snapshot.get_remotes
    monkeypatch.setattr(repo_snapshot, "get_remotes", lambda r: chamadas.append(r) or original(r))

    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.remotes == ["origin"]
    assert chamadas == []


def test_snapshot_head_destacado_cai_no_hash_abreviado(git_repo):
    import subprocess

    subprocess.run(["git", "-C", git_repo, "checkout", "--detach"], check=True, capture_output=True)

    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.branch and snapshot.branch != "main"
