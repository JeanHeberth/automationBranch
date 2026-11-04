import pytest

from services import commit_service
from services.commit_service import (
    _parse_status_path,
    get_changed_files_grouped,
    get_recent_commit_rows,
)


@pytest.mark.parametrize(
    "linha, esperado",
    [
        ("M  arquivo.py", "arquivo.py"),
        (" M src/modulo.py", "src/modulo.py"),
        ("?? novo.py", "novo.py"),
        ("R  antigo.py -> novo.py", "novo.py"),
        ("MM caminho com espaco.py", "caminho com espaco.py"),
    ],
)
def test_parse_status_path(linha, esperado):
    assert _parse_status_path(linha) == esperado


def test_get_changed_files_grouped_classifica_staged_e_unstaged(monkeypatch):
    saida = (
        "M  somente_staged.py\n"
        " M somente_unstaged.py\n"
        "MM staged_e_unstaged.py\n"
        "?? nao_rastreado.py\n"
        "R  origem.py -> destino.py\n"
    )
    monkeypatch.setattr(commit_service, "run_git_command", lambda *a, **k: saida)

    grupos = get_changed_files_grouped("/repo")

    assert "M | somente_staged.py" in grupos["staged"]
    assert "M | staged_e_unstaged.py" in grupos["staged"]
    assert "R | destino.py" in grupos["staged"]
    # Arquivo não rastreado não conta como staged.
    assert all("nao_rastreado.py" not in item for item in grupos["staged"])

    assert "M | somente_unstaged.py" in grupos["unstaged"]
    assert "M | staged_e_unstaged.py" in grupos["unstaged"]
    assert "? | nao_rastreado.py" in grupos["unstaged"]


def test_get_changed_files_grouped_vazio(monkeypatch):
    monkeypatch.setattr(commit_service, "run_git_command", lambda *a, **k: "")
    assert get_changed_files_grouped("/repo") == {"staged": [], "unstaged": []}


def test_get_recent_commit_rows_parseia_commit_simples(monkeypatch):
    linha = "* abc1234\x01Corrige bug\x01Alice\x01def5678\x01 (HEAD -> main)"
    monkeypatch.setattr(commit_service, "run_git_command", lambda *a, **k: linha)

    rows = get_recent_commit_rows("/repo", "main")

    assert len(rows) == 1
    row = rows[0]
    assert row["hash"] == "abc1234"
    assert row["subject"] == "Corrige bug"
    assert row["author"] == "Alice"
    assert row["parents"] == ["def5678"]
    assert row["is_merge"] is False
    assert row["graph"].strip() == "*"


def test_get_recent_commit_rows_detecta_merge(monkeypatch):
    linha = "*   abcdef1\x01Merge branch\x01Bob\x01aaa111 bbb222\x01"
    monkeypatch.setattr(commit_service, "run_git_command", lambda *a, **k: linha)

    rows = get_recent_commit_rows("/repo", "main")

    assert rows[0]["parents"] == ["aaa111", "bbb222"]
    assert rows[0]["is_merge"] is True


def test_get_recent_commit_rows_ignora_linhas_sem_separador(monkeypatch):
    saida = "| \\\n* abc1234\x01Assunto\x01Alice\x01\x01"
    monkeypatch.setattr(commit_service, "run_git_command", lambda *a, **k: saida)

    rows = get_recent_commit_rows("/repo", "main")
    assert len(rows) == 1


def _git_out(repo, *args):
    import subprocess
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_commit_selected_files_commita_so_selecionados(git_repo):
    from services.commit_service import commit_selected_files

    (open(f"{git_repo}/a.txt", "w")).write("a")
    (open(f"{git_repo}/b.txt", "w")).write("b")
    (open(f"{git_repo}/README.md", "a")).write("mais\n")

    commit_selected_files(git_repo, "so a", ["a.txt"])

    assert _git_out(git_repo, "show", "--name-only", "--format=").splitlines() == ["a.txt"]
    status = _git_out(git_repo, "status", "--short")
    assert "b.txt" in status and "README.md" in status


def test_commit_selected_files_preserva_stage_de_nao_selecionados(git_repo):
    from services.commit_service import commit_selected_files

    (open(f"{git_repo}/a.txt", "w")).write("a")
    (open(f"{git_repo}/b.txt", "w")).write("b")
    _git_out(git_repo, "add", "b.txt")

    commit_selected_files(git_repo, "so a", ["a.txt"])

    assert _git_out(git_repo, "diff", "--cached", "--name-only") == "b.txt"


def test_commit_selected_files_inclui_renomeacao_completa(git_repo):
    from services.commit_service import commit_selected_files

    _git_out(git_repo, "mv", "README.md", "LEIAME.md")

    commit_selected_files(git_repo, "renomeia", ["LEIAME.md"])

    assert _git_out(git_repo, "status", "--short") == ""


def test_commit_selected_files_valida_entradas(git_repo):
    import pytest
    from services.commit_service import commit_selected_files
    from services.git_runner import GitServiceError

    with pytest.raises(GitServiceError):
        commit_selected_files(git_repo, "  ", ["a.txt"])
    with pytest.raises(GitServiceError):
        commit_selected_files(git_repo, "msg", [])
