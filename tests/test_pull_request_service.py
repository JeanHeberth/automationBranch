import pytest

from services import pull_request_service
from services.pull_request_service import (
    _parse_github_repo,
    find_open_pull_request_by_head,
    invalidate_pull_request_cache,
    list_open_pull_requests,
)


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return [
            {
                "number": 1,
                "title": "A",
                "head": {"ref": "feature/a"},
                "base": {"ref": "main"},
                "html_url": "https://example/1",
            }
        ]


@pytest.fixture
def pr_env(monkeypatch):
    invalidate_pull_request_cache()
    monkeypatch.setattr(pull_request_service, "_get_repo_info", lambda repo: ("owner", "repo"))
    monkeypatch.setattr(pull_request_service, "_get_headers", lambda **k: {})

    chamadas = {"n": 0}

    def fake_get(*a, **k):
        chamadas["n"] += 1
        return _FakeResp()

    monkeypatch.setattr(pull_request_service.requests, "get", fake_get)
    yield chamadas
    invalidate_pull_request_cache()


def test_list_open_pull_requests_usa_cache(pr_env):
    a = list_open_pull_requests("/repo")
    b = list_open_pull_requests("/repo")

    assert pr_env["n"] == 1  # só uma chamada HTTP
    assert a == b


def test_use_cache_false_ignora_cache(pr_env):
    list_open_pull_requests("/repo")
    list_open_pull_requests("/repo", use_cache=False)

    assert pr_env["n"] == 2


def test_invalidate_pull_request_cache(pr_env):
    list_open_pull_requests("/repo")
    invalidate_pull_request_cache()
    list_open_pull_requests("/repo")

    assert pr_env["n"] == 2


def test_cache_expira_apos_ttl(pr_env, monkeypatch):
    relogio = {"t": 1000.0}
    monkeypatch.setattr(pull_request_service.time, "monotonic", lambda: relogio["t"])

    list_open_pull_requests("/repo")
    relogio["t"] += pull_request_service._PR_CACHE_TTL + 1
    list_open_pull_requests("/repo")

    assert pr_env["n"] == 2


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
