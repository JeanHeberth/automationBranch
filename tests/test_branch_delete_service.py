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
