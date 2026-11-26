import pytest

from services import branch_delete_service
from services.branch_delete_service import (
    filter_deletable,
    get_deletable_remote_branches,
    is_protected,
)


@pytest.mark.parametrize(
    "nome, protegida",
    [
        ("main", True),
        ("MASTER", True),
        ("  develop  ", True),
        ("developer", True),
        ("feature/x", False),
        ("bugfix/login", False),
    ],
)
def test_is_protected(nome, protegida):
    assert is_protected(nome) is protegida


def test_filter_deletable_remove_protegidas_e_vazias():
    entrada = ["main", "feature/a", "", "develop", "hotfix/b"]
    assert filter_deletable(entrada) == ["feature/a", "hotfix/b"]


def test_get_deletable_remote_branches(monkeypatch):
    monkeypatch.setattr(
        branch_delete_service,
        "get_remote_branches",
        lambda repo: ["origin/main", "origin/HEAD -> origin/main", "origin/feature/x"],
    )

    assert get_deletable_remote_branches("/repo") == ["feature/x"]


def test_get_protected_remote_branches_ordena_e_exclui(monkeypatch):
    monkeypatch.setattr(
        branch_delete_service,
        "get_remote_branches",
        lambda repo: ["origin/develop", "origin/feature/x", "origin/main", "origin/master"],
    )

    assert branch_delete_service.get_protected_remote_branches("/repo") == ["main", "master", "develop"]
    assert branch_delete_service.get_protected_remote_branches("/repo", exclude="main") == ["master", "develop"]


def test_get_protected_remote_branches_fallback_main(monkeypatch):
    monkeypatch.setattr(branch_delete_service, "get_remote_branches", lambda repo: ["origin/feature/x"])

    assert branch_delete_service.get_protected_remote_branches("/repo") == ["main"]


def _remotas(monkeypatch, *nomes):
    monkeypatch.setattr(branch_delete_service, "get_remote_branches", lambda repo: [f"origin/{n}" for n in nomes])


@pytest.mark.parametrize("atual", ["feature/x", "bugfix/y", "hotfix/z", "release/1.0"])
def test_get_pr_base_branch_de_qualquer_branch_vai_para_develop(monkeypatch, atual):
    _remotas(monkeypatch, "main", "develop", atual)

    assert branch_delete_service.get_pr_base_branch("/repo", atual) == "develop"


def test_get_pr_base_branch_da_develop_vai_para_main(monkeypatch):
    _remotas(monkeypatch, "main", "develop")

    assert branch_delete_service.get_pr_base_branch("/repo", "develop") == "main"


def test_get_pr_base_branch_da_develop_usa_master_se_nao_tem_main(monkeypatch):
    _remotas(monkeypatch, "master", "develop")

    assert branch_delete_service.get_pr_base_branch("/repo", "develop") == "master"


def test_get_pr_base_branch_sem_develop_no_remote_nao_cai_na_main(monkeypatch):
    _remotas(monkeypatch, "main", "feature/x")

    with pytest.raises(ValueError, match="develop"):
        branch_delete_service.get_pr_base_branch("/repo", "feature/x")


def test_get_deletable_remote_branches_ignora_outros_remotes_e_protegidas(monkeypatch):
    monkeypatch.setattr(
        branch_delete_service,
        "get_remote_branches",
        lambda repo: ["origin/main", "origin/feature/x", "upstream/feature/y", "origin/develop"],
    )

    assert get_deletable_remote_branches("/repo") == ["feature/x"]
