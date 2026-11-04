import os
import subprocess

import pytest

from services.branch_service import checkout_branch
from services.git_runner import GitServiceError
from services.repo_snapshot import collect_repo_snapshot
from services.stash_service import (
    apply_stash,
    drop_stash,
    get_stash_diff,
    list_stashes,
    stash_changes,
)


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", repo, *args], check=check, capture_output=True, text=True
    ).stdout.strip()


def _write(repo, name, content):
    with open(os.path.join(repo, name), "w", encoding="utf-8") as handle:
        handle.write(content)


def test_stash_de_arquivos_selecionados_deixa_o_resto(git_repo):
    _write(git_repo, "a.txt", "a")
    _write(git_repo, "b.txt", "b")

    stash_changes(git_repo, "so a", ["a.txt"])

    assert not os.path.exists(os.path.join(git_repo, "a.txt"))
    assert os.path.exists(os.path.join(git_repo, "b.txt"))
    stashes = list_stashes(git_repo)
    assert len(stashes) == 1
    assert stashes[0]["ref"] == "stash@{0}"
    assert stashes[0]["message"] == "so a"
    assert stashes[0]["branch"] == "main"


def test_stash_de_tudo_inclui_arquivos_novos_e_modificados(git_repo):
    _write(git_repo, "README.md", "alterado\n")
    _write(git_repo, "novo.txt", "x")

    stash_changes(git_repo, "tudo")

    assert _git(git_repo, "status", "--short") == ""
    assert "novo.txt" in get_stash_diff(git_repo, "stash@{0}")


def test_stash_sem_alteracoes_levanta_erro(git_repo):
    with pytest.raises(GitServiceError, match="Não há alterações"):
        stash_changes(git_repo, "nada")


def test_stash_sem_arquivos_selecionados_levanta_erro(git_repo):
    with pytest.raises(GitServiceError):
        stash_changes(git_repo, "x", [])


def test_stash_de_renomeacao_leva_origem_junto(git_repo):
    _git(git_repo, "mv", "README.md", "LEIAME.md")

    stash_changes(git_repo, "rename", ["LEIAME.md"])

    assert _git(git_repo, "status", "--short") == ""


def test_apply_mantem_e_pop_remove_o_stash(git_repo):
    _write(git_repo, "a.txt", "a")
    stash_changes(git_repo, "um")

    apply_stash(git_repo, "stash@{0}")
    assert os.path.exists(os.path.join(git_repo, "a.txt"))
    assert len(list_stashes(git_repo)) == 1

    os.remove(os.path.join(git_repo, "a.txt"))
    _git(git_repo, "clean", "-fdq")
    apply_stash(git_repo, "stash@{0}", drop=True)
    assert os.path.exists(os.path.join(git_repo, "a.txt"))
    assert list_stashes(git_repo) == []


def test_drop_remove_o_stash(git_repo):
    _write(git_repo, "a.txt", "a")
    stash_changes(git_repo, "descartar")

    drop_stash(git_repo, "stash@{0}")

    assert list_stashes(git_repo) == []


def test_pop_com_conflito_mantem_o_stash(git_repo):
    _write(git_repo, "README.md", "versao do stash\n")
    stash_changes(git_repo, "conflito")
    _write(git_repo, "README.md", "versao local\n")
    _git(git_repo, "commit", "-qam", "muda local")

    with pytest.raises(GitServiceError):
        apply_stash(git_repo, "stash@{0}", drop=True)

    assert len(list_stashes(git_repo)) == 1


def test_ordem_dos_stashes_mais_recente_primeiro(git_repo):
    _write(git_repo, "a.txt", "a")
    stash_changes(git_repo, "primeiro")
    _write(git_repo, "b.txt", "b")
    stash_changes(git_repo, "segundo")

    assert [s["message"] for s in list_stashes(git_repo)] == ["segundo", "primeiro"]


def test_snapshot_inclui_stashes(git_repo):
    _write(git_repo, "a.txt", "a")
    stash_changes(git_repo, "no snapshot")

    snapshot = collect_repo_snapshot(git_repo)

    assert snapshot.stashes_error is None
    assert [s["message"] for s in snapshot.stashes] == ["no snapshot"]


def test_checkout_bloqueado_menciona_overwritten_e_stash_resolve(git_repo):
    # Garante a mensagem em que a UI se apoia para oferecer o stash.
    _git(git_repo, "checkout", "-qb", "outra")
    _write(git_repo, "README.md", "na outra\n")
    _git(git_repo, "commit", "-qam", "muda na outra")
    _git(git_repo, "checkout", "-q", "main")
    _write(git_repo, "README.md", "local sujo\n")

    with pytest.raises(GitServiceError) as exc_info:
        checkout_branch(git_repo, "outra")
    assert "overwritten by checkout" in str(exc_info.value).lower()

    stash_changes(git_repo, "antes de trocar")
    checkout_branch(git_repo, "outra")
    assert _git(git_repo, "branch", "--show-current") == "outra"


def test_pop_de_renomeacao_volta_sem_conflito(git_repo):
    _git(git_repo, "mv", "README.md", "LEIAME.md")
    stash_changes(git_repo, "rename", ["LEIAME.md"])
    assert _git(git_repo, "status", "--short") == ""

    apply_stash(git_repo, "stash@{0}", drop=True)

    assert os.path.exists(os.path.join(git_repo, "LEIAME.md"))
    assert not os.path.exists(os.path.join(git_repo, "README.md"))
