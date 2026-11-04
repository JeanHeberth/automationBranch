import os
import subprocess

import pytest

from services.commit_service import get_commit_diff
from services.search_service import (
    filter_branches,
    filter_paths,
    get_file_history,
    list_repo_files,
    search_commits,
)


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo, name, content, message, author=None):
    path = os.path.join(repo, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    _git(repo, "add", "-A")
    args = ["commit", "-q", "-m", message]
    if author:
        args += ["--author", f"{author} <{author.lower().replace(' ', '')}@x.com>"]
    _git(repo, *args)
    return _git(repo, "rev-parse", "--short", "HEAD")


@pytest.fixture
def repo(git_repo):
    _commit(git_repo, "src/app.py", "print('um')\n", "Adiciona o app")
    _commit(git_repo, "src/util.py", "def calcular_imposto(): pass\n", "Cria util", author="Maria Silva")
    _commit(git_repo, "docs/guia.md", "# guia\n", "Escreve guia de uso")
    return git_repo


def test_busca_por_mensagem_ignora_maiusculas(repo):
    rows = search_commits(repo, "GUIA", "message")

    assert [r["subject"] for r in rows] == ["Escreve guia de uso"]
    assert set(rows[0]) == {"hash", "subject", "author", "date"}


def test_busca_por_autor(repo):
    rows = search_commits(repo, "maria", "author")

    assert [r["subject"] for r in rows] == ["Cria util"]
    assert rows[0]["author"] == "Maria Silva"


def test_busca_por_codigo_acha_quem_adicionou_o_texto(repo):
    rows = search_commits(repo, "calcular_imposto", "code")

    assert [r["subject"] for r in rows] == ["Cria util"]


def test_busca_por_hash_traz_o_commit_primeiro(repo):
    target = _git(repo, "rev-parse", "--short", "HEAD~1")

    rows = search_commits(repo, target, "message")

    assert rows[0]["hash"] == target


def test_busca_acha_commits_de_outras_branches(repo):
    _git(repo, "checkout", "-qb", "outra")
    _commit(repo, "x.txt", "x", "Trabalho exclusivo da outra")
    _git(repo, "checkout", "-q", "main")

    assert [r["subject"] for r in search_commits(repo, "exclusivo", "message")] == ["Trabalho exclusivo da outra"]


def test_texto_digitado_nao_e_expressao_regular(repo):
    # "(" quebraria uma regex; como texto literal simplesmente não acha nada.
    assert search_commits(repo, "(", "message") == []
    assert search_commits(repo, ".*", "message") == []


def test_busca_vazia_ou_modo_invalido(repo):
    assert search_commits(repo, "   ", "message") == []
    with pytest.raises(ValueError):
        search_commits(repo, "x", "inexistente")


def test_busca_respeita_o_limite(repo):
    assert len(search_commits(repo, "a", "message", limit=2)) <= 2


def test_historico_do_arquivo_segue_renomeacao(repo):
    _git(repo, "mv", "src/util.py", "src/utilitarios.py")
    _git(repo, "commit", "-qm", "Renomeia util")

    subjects = [r["subject"] for r in get_file_history(repo, "src/utilitarios.py")]

    assert subjects == ["Renomeia util", "Cria util"]


def test_list_repo_files_inclui_novos_e_ignora_ignorados(repo):
    with open(os.path.join(repo, ".gitignore"), "w") as handle:
        handle.write("*.log\n")
    for name in ("novo.txt", "debug.log"):
        with open(os.path.join(repo, name), "w") as handle:
            handle.write("x")

    files = list_repo_files(repo)

    assert "src/app.py" in files and "novo.txt" in files
    assert "debug.log" not in files


def test_list_repo_files_com_acento_no_nome(repo):
    with open(os.path.join(repo, "relatório.txt"), "w") as handle:
        handle.write("x")

    assert "relatório.txt" in list_repo_files(repo)


def test_get_commit_diff_traz_resumo_e_patch(repo):
    diff = get_commit_diff(repo, "HEAD")

    assert "Escreve guia de uso" in diff
    assert "docs/guia.md" in diff
    assert "+# guia" in diff


def test_filter_paths_ordena_nome_antes_de_caminho():
    paths = ["src/app/controller.py", "app.py", "docs/app-guide.md", "lib/x/app_test.py", "z/readme.md"]

    assert filter_paths(paths, "app") == ["app.py", "docs/app-guide.md", "lib/x/app_test.py", "src/app/controller.py"]


def test_filter_paths_todas_as_palavras_e_sem_diferenciar_maiusculas():
    paths = ["src/Auth/LoginService.py", "src/auth/token.py", "tests/test_login.py"]

    assert filter_paths(paths, "auth login") == ["src/Auth/LoginService.py"]
    assert filter_paths(paths, "") == []
    assert filter_paths(paths, "naoexiste") == []


def test_filter_paths_respeita_o_limite():
    assert len(filter_paths([f"a{i}.py" for i in range(500)], "a", limit=10)) == 10


def test_filter_branches_remota_so_aparece_sem_local_correspondente():
    local = ["main", "feature/login"]
    remote = ["origin/main", "origin/feature/login", "origin/feature/busca"]

    assert filter_branches(local, remote, "feature") == [
        {"name": "feature/login", "remote": False},
        {"name": "origin/feature/busca", "remote": True},
    ]
    assert filter_branches(local, remote, "") == []


# --- conteúdo dos arquivos ---

from services.git_runner import GitServiceError, run_git_command  # noqa: E402
from services.search_service import read_file_for_view, search_content  # noqa: E402


@pytest.fixture
def content_repo(git_repo):
    _commit(git_repo, "src/util.py", "def calcular_imposto():\n    return 1\n# Calcular de novo\n", "util")
    _commit(git_repo, "a b.txt", "x: y\ncalcular\n", "espaco")
    return git_repo


def test_search_content_acha_linha_e_arquivo_ignorando_maiusculas(content_repo):
    rows = search_content(content_repo, "calcular")

    assert {"path": "src/util.py", "line": 1, "text": "def calcular_imposto():"} in rows
    assert {"path": "src/util.py", "line": 3, "text": "# Calcular de novo"} in rows
    assert {"path": "a b.txt", "line": 2, "text": "calcular"} in rows


def test_search_content_sem_resultado_nao_e_erro(content_repo):
    assert search_content(content_repo, "texto-que-nao-existe") == []


def test_search_content_inclui_arquivo_novo_e_acento_e_ignora_gitignore(content_repo):
    with open(os.path.join(content_repo, ".gitignore"), "w") as handle:
        handle.write("*.log\n")
    for name, body in (("novo.txt", "calcular novo\n"), ("relatório.txt", "café calcular\n"), ("x.log", "calcular\n")):
        with open(os.path.join(content_repo, name), "w", encoding="utf-8") as handle:
            handle.write(body)

    paths = {row["path"] for row in search_content(content_repo, "calcular")}

    assert {"novo.txt", "relatório.txt"} <= paths
    assert "x.log" not in paths


def test_search_content_pula_binarios(content_repo):
    with open(os.path.join(content_repo, "bin.dat"), "wb") as handle:
        handle.write(b"calcular\x00\x01")

    assert "bin.dat" not in {row["path"] for row in search_content(content_repo, "calcular")}


def test_search_content_texto_literal_e_consulta_curta(content_repo):
    assert search_content(content_repo, "(") == []   # curta demais
    assert search_content(content_repo, ".*") == []   # regex não é interpretada
    assert search_content(content_repo, "  ") == []


def test_search_content_limita_ocorrencias_por_arquivo_e_total(content_repo):
    with open(os.path.join(content_repo, "grande.txt"), "w") as handle:
        handle.write("alvo\n" * 50)

    rows = search_content(content_repo, "alvo")
    assert len(rows) == 5  # máximo por arquivo

    for i in range(10):
        with open(os.path.join(content_repo, f"f{i}.txt"), "w") as handle:
            handle.write("alvo\n")
    assert len(search_content(content_repo, "alvo", limit=7)) == 7


def test_search_content_trunca_linha_muito_longa(content_repo):
    with open(os.path.join(content_repo, "longa.txt"), "w") as handle:
        handle.write("alvo " + "x" * 1000 + "\n")

    assert len(search_content(content_repo, "alvo")[0]["text"]) == 160


def test_search_content_erro_real_do_git_continua_sendo_erro(tmp_path):
    with pytest.raises(GitServiceError):
        search_content(str(tmp_path), "qualquer")  # não é um repositório


def test_run_git_command_aceita_codigos_de_saida_informados(git_repo):
    # git grep sai com 1 sem resultados: com (0, 1) devolve vazio, sem (padrão) levanta.
    assert run_git_command(git_repo, ["grep", "-F", "nada-aqui"], ok_returncodes=(0, 1)) == ""
    with pytest.raises(GitServiceError):
        run_git_command(git_repo, ["grep", "-F", "nada-aqui"])


def test_read_file_for_view(content_repo):
    assert "def calcular_imposto" in read_file_for_view(content_repo, "src/util.py")

    with open(os.path.join(content_repo, "b.bin"), "wb") as handle:
        handle.write(b"\x00\x01")
    with pytest.raises(GitServiceError, match="binário"):
        read_file_for_view(content_repo, "b.bin")
    with pytest.raises(GitServiceError):
        read_file_for_view(content_repo, "nao-existe.txt")
