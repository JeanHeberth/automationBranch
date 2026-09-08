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
