import pytest

from services import pull_request_service
from services.pull_request_service import (
    _parse_github_repo,
    find_open_pull_request_by_head,
)


@pytest.mark.parametrize(
    "url, esperado",
    [
        ("git@github.com:owner/repo.git", ("owner", "repo")),
        ("git@github.com:owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo.name.git", ("owner", "repo.name")),
        ("", (None, None)),
        ("https://gitlab.com/owner/repo.git", (None, None)),
    ],
)
def test_parse_github_repo(url, esperado):
    assert _parse_github_repo(url) == esperado


def test_find_open_pull_request_by_head_encontra(monkeypatch):
    prs = [
        {"number": 1, "head": "feature/a", "title": "A"},
        {"number": 2, "head": "feature/b", "title": "B"},
    ]
    monkeypatch.setattr(
        pull_request_service, "list_open_pull_requests", lambda repo: prs
    )

    assert find_open_pull_request_by_head("/repo", "feature/b")["number"] == 2
    assert find_open_pull_request_by_head("/repo", "feature/z") is None
