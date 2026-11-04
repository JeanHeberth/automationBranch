import os
import subprocess

import pytest

from services import git_actions_service as ga
from services.git_runner import GitServiceError
from services.sync_service import git_pull


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(repo, name, content):
    path = os.path.join(repo, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _commit(repo, name, content, message):
    _write(repo, name, content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "--short", "HEAD")


def _branch(repo, name):
    _git(repo, "checkout", "-q", "-b", name)


@pytest.fixture
def repo(git_repo):
    _branch(git_repo, "feature/x")  # a conftest deixa na main (protegida)
    return git_repo


@pytest.fixture
def conflicting(git_repo):
    """main e feature/a alteram a mesma linha: merge/rebase/cherry-pick conflitam."""
    _commit(git_repo, "f.txt", "base\n", "base")
    _branch(git_repo, "feature/a")
    _commit(git_repo, "f.txt", "da feature\n", "feature muda f")
    _git(git_repo, "checkout", "-q", "main")
    _commit(git_repo, "f.txt", "da main\n", "main muda f")
    return git_repo


# ---------- operação em andamento ----------

def test_sem_operacao_em_andamento(repo):
    assert ga.get_operation_in_progress(repo) is None
    with pytest.raises(GitServiceError):
        ga.abort_operation(repo)
    with pytest.raises(GitServiceError):
        ga.continue_operation(repo)


def test_merge_com_conflito_levanta_conflict_error_e_pode_abortar(conflicting):
    with pytest.raises(ga.ConflictError) as exc_info:
        ga.merge_branch(conflicting, "feature/a")

    assert exc_info.value.operation == "merge"
    assert ga.get_operation_in_progress(conflicting) == "merge"

    ga.abort_operation(conflicting)

    assert ga.get_operation_in_progress(conflicting) is None
    assert _git(conflicting, "status", "--short") == ""


def test_merge_com_conflito_resolvido_pode_continuar(conflicting):
    with pytest.raises(ga.ConflictError):
        ga.merge_branch(conflicting, "feature/a")

    _write(conflicting, "f.txt", "resolvido\n")
    _git(conflicting, "add", "f.txt")
    ga.continue_operation(conflicting)

    assert ga.get_operation_in_progress(conflicting) is None
    assert len(_git(conflicting, "log", "-1", "--format=%P").split()) == 2  # commit de merge


def test_continue_sem_resolver_conflito_falha_e_mantem_a_operacao(conflicting):
    with pytest.raises(ga.ConflictError):
        ga.merge_branch(conflicting, "feature/a")

    with pytest.raises(GitServiceError):
        ga.continue_operation(conflicting)

    assert ga.get_operation_in_progress(conflicting) == "merge"


# ---------- merge / rebase ----------

def test_merge_sem_conflito_nao_abre_editor(repo):
    _commit(repo, "a.txt", "a\n", "a")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "m.txt", "m\n", "m")  # força merge commit (sem fast-forward)

    ga.merge_branch(repo, "feature/x")

    assert os.path.exists(os.path.join(repo, "a.txt"))
    assert ga.get_operation_in_progress(repo) is None


def test_merge_valida_entradas(repo):
    with pytest.raises(GitServiceError, match="nela mesma"):
        ga.merge_branch(repo, "feature/x")
    with pytest.raises(GitServiceError):
        ga.merge_branch(repo, "  ")
    with pytest.raises(GitServiceError):
        ga.merge_branch(repo, "nao-existe")


def test_rebase_reaplica_os_commits(repo):
    _commit(repo, "a.txt", "a\n", "na feature")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "m.txt", "m\n", "na main")
    _git(repo, "checkout", "-q", "feature/x")

    ga.rebase_onto(repo, "main")

    assert _git(repo, "log", "--format=%s", "-3").splitlines() == ["na feature", "na main", "primeiro commit"]


def test_rebase_com_conflito_e_abortar(conflicting):
    _git(conflicting, "checkout", "-q", "feature/a")

    with pytest.raises(ga.ConflictError) as exc_info:
        ga.rebase_onto(conflicting, "main")

    assert exc_info.value.operation == "rebase"
    ga.abort_operation(conflicting)
    assert ga.get_operation_in_progress(conflicting) is None


def test_rebase_com_conflito_resolvido_continua(conflicting):
    _git(conflicting, "checkout", "-q", "feature/a")
    with pytest.raises(ga.ConflictError):
        ga.rebase_onto(conflicting, "main")

    _write(conflicting, "f.txt", "resolvido\n")
    _git(conflicting, "add", "f.txt")
    ga.continue_operation(conflicting)

    assert ga.get_operation_in_progress(conflicting) is None
    assert _git(conflicting, "log", "-1", "--format=%s") == "feature muda f"


def test_rebase_recusa_branch_protegida_e_entradas_invalidas(git_repo):
    with pytest.raises(GitServiceError, match="protegida"):
        ga.rebase_onto(git_repo, "outra")


def test_rebase_valida_entradas(repo):
    with pytest.raises(GitServiceError, match="nela mesma"):
        ga.rebase_onto(repo, "feature/x")
    with pytest.raises(GitServiceError):
        ga.rebase_onto(repo, "")


# ---------- cherry-pick / revert ----------

def test_cherry_pick_traz_o_commit(repo):
    _git(repo, "checkout", "-q", "main")
    _branch(repo, "feature/outra")
    sha = _commit(repo, "c.txt", "c\n", "commit a copiar")
    _git(repo, "checkout", "-q", "feature/x")

    ga.cherry_pick(repo, sha)

    assert _git(repo, "log", "-1", "--format=%s") == "commit a copiar"


def test_cherry_pick_com_conflito(conflicting):
    sha = _git(conflicting, "rev-parse", "feature/a")

    with pytest.raises(ga.ConflictError) as exc_info:
        ga.cherry_pick(conflicting, sha)

    assert exc_info.value.operation == "cherry-pick"
    ga.abort_operation(conflicting)
    assert ga.get_operation_in_progress(conflicting) is None


def test_revert_cria_commit_inverso(repo):
    sha = _commit(repo, "r.txt", "r\n", "para reverter")

    ga.revert_commit(repo, sha)

    assert _git(repo, "log", "-1", "--format=%s").startswith('Revert "para reverter"')
    assert not os.path.exists(os.path.join(repo, "r.txt"))


def test_cherry_pick_e_revert_recusam_merge_commit(repo):
    _commit(repo, "a.txt", "a\n", "a")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "m.txt", "m\n", "m")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature/x")
    merge_sha = _git(repo, "rev-parse", "--short", "HEAD")
    _git(repo, "checkout", "-q", "feature/x")

    with pytest.raises(GitServiceError, match="merge commit"):
        ga.cherry_pick(repo, merge_sha)
    with pytest.raises(GitServiceError, match="merge commit"):
        ga.revert_commit(repo, merge_sha)


# ---------- desfazer / reflog ----------

def test_undo_last_commit_mantem_alteracoes_em_stage(repo):
    _commit(repo, "a.txt", "a\n", "vai ser desfeito")

    summary = ga.undo_last_commit(repo)

    assert summary.endswith("vai ser desfeito")
    assert _git(repo, "log", "-1", "--format=%s") == "primeiro commit"
    assert _git(repo, "diff", "--cached", "--name-only") == "a.txt"


def test_undo_last_commit_recusa_protegida_e_primeiro_commit(git_repo, tmp_path):
    with pytest.raises(GitServiceError, match="protegida"):
        ga.undo_last_commit(git_repo)

    solo = str(tmp_path / "solo")
    os.makedirs(solo)
    subprocess.run(["git", "init", "-q", "-b", "feature/solo", solo], check=True)
    _git(solo, "config", "user.email", "t@t.com")
    _git(solo, "config", "user.name", "T")
    _commit(solo, "a.txt", "a\n", "unico")
    with pytest.raises(GitServiceError, match="primeiro commit"):
        ga.undo_last_commit(solo)


def test_reflog_lista_entradas_recentes_primeiro(repo):
    _commit(repo, "a.txt", "a\n", "um")
    _commit(repo, "b.txt", "b\n", "dois")

    entries = ga.get_reflog(repo)

    assert entries[0]["selector"] == "HEAD@{0}"
    assert "commit: dois" in entries[0]["message"]
    assert set(entries[0]) == {"hash", "selector", "message", "date"}
    assert len(ga.get_reflog(repo, limit=2)) == 2


def test_reset_hard_volta_a_um_ponto_do_reflog(repo):
    first = _commit(repo, "a.txt", "a\n", "um")
    _commit(repo, "b.txt", "b\n", "dois")

    ga.reset_hard(repo, first)

    assert _git(repo, "log", "-1", "--format=%s") == "um"
    assert not os.path.exists(os.path.join(repo, "b.txt"))
    # e o commit "dois" continua recuperável pelo reflog
    assert any("dois" in e["message"] for e in ga.get_reflog(repo))


def test_reset_hard_recusa_protegida_e_alteracoes_nao_commitadas(git_repo, repo):
    with pytest.raises(GitServiceError, match="protegida"):
        _git(repo, "checkout", "-q", "main")
        ga.reset_hard(repo, "HEAD")

    _git(repo, "checkout", "-q", "feature/x")
    _write(repo, "README.md", "alterado\n")
    with pytest.raises(GitServiceError, match="não commitadas"):
        ga.reset_hard(repo, "HEAD")
    assert "alterado" in open(os.path.join(repo, "README.md")).read()  # nada foi perdido


def test_reset_hard_ignora_arquivo_novo_nao_rastreado(repo):
    _write(repo, "novo.txt", "x")

    assert ga.is_working_tree_clean(repo) is True
    ga.reset_hard(repo, "HEAD")
    assert os.path.exists(os.path.join(repo, "novo.txt"))


# ---------- branches e tags ----------

def test_create_branch_at(repo):
    sha = _commit(repo, "a.txt", "a\n", "um")
    _commit(repo, "b.txt", "b\n", "dois")

    ga.create_branch_at(repo, "recuperada", sha)

    assert _git(repo, "rev-parse", "--short", "recuperada") == sha


@pytest.mark.parametrize("nome", ["", "  ", "com espaço", "a..b", "~x", "x.lock", "-inicio"])
def test_nomes_de_branch_invalidos(repo, nome):
    with pytest.raises(GitServiceError):
        ga.create_branch_at(repo, nome, "HEAD")


def test_rename_branch(repo):
    message = ga.rename_branch(repo, "feature/x", "feature/y")

    assert _git(repo, "branch", "--show-current") == "feature/y"
    assert "renomeada" in message and "continua como" not in message


def test_rename_branch_avisa_quando_havia_upstream(repo, tmp_path):
    remote = str(tmp_path / "remote.git")
    subprocess.run(["git", "init", "--bare", "-q", remote], check=True)
    _git(repo, "remote", "add", "origin", remote)
    _git(repo, "push", "-q", "-u", "origin", "feature/x")

    message = ga.rename_branch(repo, "feature/x", "feature/y")

    assert "continua como 'feature/x'" in message


def test_rename_branch_recusa_protegida_nome_igual_e_invalido(git_repo, repo):
    with pytest.raises(GitServiceError, match="protegida"):
        ga.rename_branch(repo, "main", "outra")
    with pytest.raises(GitServiceError, match="igual"):
        ga.rename_branch(repo, "feature/x", "feature/x")
    with pytest.raises(GitServiceError, match="válido"):
        ga.rename_branch(repo, "feature/x", "nome ruim")


def test_tags_criar_listar_apagar(repo):
    ga.create_tag(repo, "v1.0", "primeira versão")
    ga.create_tag(repo, "v1.1")

    tags = {t["name"]: t for t in ga.list_tags(repo)}

    assert tags["v1.0"]["annotated"] is True and tags["v1.0"]["subject"] == "primeira versão"
    assert tags["v1.1"]["annotated"] is False
    assert set(tags["v1.0"]) == {"name", "annotated", "date", "subject"}

    ga.delete_tag(repo, "v1.1")
    assert [t["name"] for t in ga.list_tags(repo)] == ["v1.0"]


def test_tag_com_nome_invalido_ou_repetido(repo):
    with pytest.raises(GitServiceError, match="válido"):
        ga.create_tag(repo, "com espaço")
    ga.create_tag(repo, "v1")
    with pytest.raises(GitServiceError):
        ga.create_tag(repo, "v1")


def test_tags_enviar_e_apagar_no_remoto(repo, tmp_path):
    remote = str(tmp_path / "remote.git")
    subprocess.run(["git", "init", "--bare", "-q", remote], check=True)
    _git(repo, "remote", "add", "origin", remote)
    ga.create_tag(repo, "v1")

    ga.push_tag(repo, "v1")
    assert "refs/tags/v1" in _git(remote, "show-ref")

    ga.delete_remote_tag(repo, "v1")
    assert _git(remote, "tag") == ""


def test_merged_branches_exclui_protegidas_atual_e_nao_mescladas(git_repo):
    for name in ("feature/pronta", "feature/outra-pronta"):
        _git(git_repo, "checkout", "-q", "-b", name)
        _commit(git_repo, f"{name.split('/')[1]}.txt", "x\n", name)
        _git(git_repo, "checkout", "-q", "main")
        _git(git_repo, "merge", "-q", "--no-ff", "-m", f"merge {name}", name)
    _git(git_repo, "checkout", "-q", "-b", "feature/em-andamento")
    _commit(git_repo, "wip.txt", "x\n", "wip")
    _git(git_repo, "branch", "develop", "main")

    merged = ga.get_merged_branches(git_repo, "main")

    assert sorted(merged) == ["feature/outra-pronta", "feature/pronta"]


# ---------- clonar e inicializar ----------

@pytest.mark.parametrize(
    "url, nome",
    [
        ("https://github.com/o/meu-repo.git", "meu-repo"),
        ("https://github.com/o/meu-repo", "meu-repo"),
        ("https://github.com/o/meu-repo/", "meu-repo"),
        ("git@github.com:o/meu-repo.git", "meu-repo"),
        ("ssh://git@gitlab.com:22/grupo/sub/meu-repo.git", "meu-repo"),
        ("/tmp/algum/caminho/repo.git", "repo"),
    ],
)
def test_repo_name_from_url(url, nome):
    assert ga.repo_name_from_url(url) == nome


def test_clone_e_validacoes(git_repo, tmp_path):
    destino = str(tmp_path / "clones")
    os.makedirs(destino)

    caminho = ga.clone_repository(git_repo, destino)

    assert caminho == os.path.join(destino, os.path.basename(git_repo))
    assert os.path.exists(os.path.join(caminho, "README.md"))

    with pytest.raises(GitServiceError, match="já existe"):
        ga.clone_repository(git_repo, destino)
    with pytest.raises(GitServiceError, match="não existe"):
        ga.clone_repository(git_repo, str(tmp_path / "nada"))
    with pytest.raises(GitServiceError):
        ga.clone_repository("   ", destino)


def test_clone_de_url_inexistente_falha(tmp_path):
    with pytest.raises(GitServiceError):
        ga.clone_repository(str(tmp_path / "nao-e-repo"), str(tmp_path))


def test_init_repository(tmp_path):
    pasta = str(tmp_path / "novo")
    os.makedirs(pasta)

    assert ga.init_repository(pasta) == pasta
    assert os.path.isdir(os.path.join(pasta, ".git"))

    with pytest.raises(GitServiceError, match="já é um repositório"):
        ga.init_repository(pasta)
    with pytest.raises(GitServiceError, match="não existe"):
        ga.init_repository(str(tmp_path / "x"))


# ---------- fetch e pull --rebase ----------

def test_fetch_all_traz_e_poda(repo, tmp_path):
    remote = str(tmp_path / "remote.git")
    subprocess.run(["git", "init", "--bare", "-q", remote], check=True)
    _git(repo, "remote", "add", "origin", remote)
    _git(repo, "push", "-q", "origin", "feature/x", "main")

    other = str(tmp_path / "other")
    subprocess.run(["git", "clone", "-q", remote, other], check=True)
    _git(other, "config", "user.email", "o@o.com")
    _git(other, "config", "user.name", "O")
    _git(other, "checkout", "-q", "-b", "feature/nova")
    _commit(other, "n.txt", "n\n", "nova")
    _git(other, "push", "-q", "origin", "feature/nova")

    assert ga.fetch_all(repo) == "Fetch concluído."
    assert "origin/feature/nova" in _git(repo, "branch", "-r")

    _git(other, "push", "-q", "origin", "--delete", "feature/nova")
    ga.fetch_all(repo)
    assert "origin/feature/nova" not in _git(repo, "branch", "-r")


def test_pull_com_rebase_mantem_historico_linear(repo, tmp_path):
    remote = str(tmp_path / "remote.git")
    subprocess.run(["git", "init", "--bare", "-q", remote], check=True)
    _git(repo, "remote", "add", "origin", remote)
    _git(repo, "push", "-q", "-u", "origin", "feature/x")

    other = str(tmp_path / "other")
    subprocess.run(["git", "clone", "-q", "-b", "feature/x", remote, other], check=True)
    _git(other, "config", "user.email", "o@o.com")
    _git(other, "config", "user.name", "O")
    _commit(other, "remoto.txt", "r\n", "commit remoto")
    _git(other, "push", "-q")

    _commit(repo, "local.txt", "l\n", "commit local")
    _write(repo, "README.md", "nao commitado\n")  # --autostash cuida disso

    git_pull(repo, rebase=True)

    assert _git(repo, "log", "--format=%s", "-2").splitlines() == ["commit local", "commit remoto"]
    assert len(_git(repo, "log", "-1", "--format=%P").split()) == 1  # sem merge commit
    assert "nao commitado" in open(os.path.join(repo, "README.md")).read()


# ---------- refazer (redo do "desfazer commit") ----------

def test_redo_traz_de_volta_o_commit_desfeito(repo):
    sha = _commit(repo, "a.txt", "a\n", "vai e volta")
    ga.undo_last_commit(repo)
    assert _git(repo, "log", "-1", "--format=%s") == "primeiro commit"

    summary = ga.redo_last_undo(repo)

    assert summary.endswith("vai e volta")
    assert _git(repo, "rev-parse", "--short", "HEAD") == sha  # o mesmo commit, sem recriá-lo
    assert _git(repo, "status", "--short") == ""


def test_redo_so_esta_disponivel_logo_depois_do_desfazer(repo):
    _commit(repo, "a.txt", "a\n", "um")

    assert ga.get_redo_target(repo) is None
    with pytest.raises(GitServiceError, match="Reflog"):
        ga.redo_last_undo(repo)

    ga.undo_last_commit(repo)
    assert ga.get_redo_target(repo)["summary"].endswith("um")


def test_redo_some_depois_de_um_novo_commit(repo):
    _commit(repo, "a.txt", "a\n", "desfeito")
    ga.undo_last_commit(repo)
    _git(repo, "commit", "-q", "-m", "novo no lugar")

    assert ga.get_redo_target(repo) is None
    with pytest.raises(GitServiceError):
        ga.redo_last_undo(repo)


def test_redo_some_depois_de_trocar_de_branch(repo):
    _commit(repo, "a.txt", "a\n", "desfeito")
    ga.undo_last_commit(repo)
    _git(repo, "stash", "-q")
    _git(repo, "checkout", "-q", "main")

    assert ga.get_redo_target(repo) is None


def test_redo_preserva_o_que_foi_alterado_depois_do_desfazer(repo):
    _commit(repo, "a.txt", "a\n", "desfeito")
    ga.undo_last_commit(repo)
    _write(repo, "extra.txt", "novo trabalho\n")

    ga.redo_last_undo(repo)

    assert os.path.exists(os.path.join(repo, "extra.txt"))
    assert "extra.txt" in _git(repo, "status", "--short")  # continua como arquivo novo, nada perdido


def test_undo_e_redo_em_sequencia_varias_vezes(repo):
    _commit(repo, "a.txt", "a\n", "ciclo")

    for _ in range(3):
        ga.undo_last_commit(repo)
        ga.redo_last_undo(repo)

    assert _git(repo, "log", "-1", "--format=%s") == "ciclo"
    assert _git(repo, "rev-list", "--count", "HEAD") == "2"


def test_redo_recusa_branch_protegida(repo):
    _commit(repo, "a.txt", "a\n", "x")
    ga.undo_last_commit(repo)
    _git(repo, "stash", "-q", "--include-untracked")
    _git(repo, "checkout", "-q", "main")

    with pytest.raises(GitServiceError, match="protegida"):
        ga.redo_last_undo(repo)
