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


def test_get_file_diff_unstaged_staged_e_novo(git_repo):
    from services.commit_service import get_file_diff

    (open(f"{git_repo}/README.md", "a")).write("linha nova\n")
    (open(f"{git_repo}/novo.txt", "w")).write("conteudo\n")

    unstaged = get_file_diff(git_repo, "README.md", staged=False)
    assert "+linha nova" in unstaged

    assert get_file_diff(git_repo, "README.md", staged=True) == "(sem diferenças)"

    _git_out(git_repo, "add", "README.md")
    assert "+linha nova" in get_file_diff(git_repo, "README.md", staged=True)

    novo = get_file_diff(git_repo, "novo.txt", staged=False, untracked=True)
    assert "+conteudo" in novo and "--- /dev/null" in novo


def test_get_file_diff_binario_e_truncamento(git_repo, monkeypatch):
    from services import commit_service
    from services.commit_service import get_file_diff

    (open(f"{git_repo}/bin.dat", "wb")).write(b"\x00\x01\x02")
    assert get_file_diff(git_repo, "bin.dat", False, untracked=True) == "(arquivo binário)"

    monkeypatch.setattr(commit_service, "MAX_DIFF_CHARS", 50)
    (open(f"{git_repo}/grande.txt", "w")).write("x\n" * 100)
    assert get_file_diff(git_repo, "grande.txt", False, untracked=True).endswith("diff truncado ...")


def test_stage_e_unstage_files(git_repo):
    from services.commit_service import stage_files, unstage_files

    (open(f"{git_repo}/a.txt", "w")).write("a")
    stage_files(git_repo, ["a.txt"])
    assert _git_out(git_repo, "diff", "--cached", "--name-only") == "a.txt"

    unstage_files(git_repo, ["a.txt"])
    assert _git_out(git_repo, "diff", "--cached", "--name-only") == ""
    assert (open(f"{git_repo}/a.txt").read()) == "a"


def test_unstage_renomeacao_completa(git_repo):
    from services.commit_service import unstage_files

    _git_out(git_repo, "mv", "README.md", "LEIAME.md")
    unstage_files(git_repo, ["LEIAME.md"])

    assert _git_out(git_repo, "diff", "--cached", "--name-only") == ""


def test_discard_changes_rastreado_e_novo(git_repo):
    import os
    from services.commit_service import discard_changes

    (open(f"{git_repo}/README.md", "a")).write("lixo\n")
    (open(f"{git_repo}/novo.txt", "w")).write("x")

    discard_changes(git_repo, ["README.md", "novo.txt"])

    assert "lixo" not in open(f"{git_repo}/README.md").read()
    assert not os.path.exists(f"{git_repo}/novo.txt")


def test_discard_preserva_o_que_esta_em_stage(git_repo):
    from services.commit_service import discard_changes

    (open(f"{git_repo}/README.md", "a")).write("no stage\n")
    _git_out(git_repo, "add", "README.md")
    (open(f"{git_repo}/README.md", "a")).write("so no disco\n")

    discard_changes(git_repo, ["README.md"])

    content = open(f"{git_repo}/README.md").read()
    assert "no stage" in content and "so no disco" not in content


def test_arquivos_com_espaco_e_acento(git_repo):
    from services.commit_service import commit_selected_files, get_changed_files_grouped

    (open(f"{git_repo}/relatório final.txt", "w")).write("x")
    grouped = get_changed_files_grouped(git_repo)
    assert grouped["unstaged"] == ["? | relatório final.txt"]

    commit_selected_files(git_repo, "acentos", ["relatório final.txt"])
    assert _git_out(git_repo, "status", "--short") == ""
