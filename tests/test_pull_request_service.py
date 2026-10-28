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
        # Formatos que antes quebravam:
        ("https://github.com/owner/repo/", ("owner", "repo")),
        ("https://github.com/owner/repo.git/", ("owner", "repo")),
        ("  https://github.com/owner/repo  ", ("owner", "repo")),
        ("ssh://git@github.com/owner/repo.git", ("owner", "repo")),
        ("ssh://git@github.com:22/owner/repo.git", ("owner", "repo")),
        ("git://github.com/owner/repo.git", ("owner", "repo")),
        ("https://user:token@github.com/owner/repo.git", ("owner", "repo")),
        ("https://www.github.com/owner/repo", ("owner", "repo")),
        # Continuam rejeitados:
        ("", (None, None)),
        ("https://gitlab.com/owner/repo.git", (None, None)),
        ("git@bitbucket.org:owner/repo.git", (None, None)),
        ("https://github.com/owner", (None, None)),
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


# ---------------------------------------------------------------------------
# Estado de merge, auto-merge e atualização de branch
# ---------------------------------------------------------------------------

import requests

from services.git_runner import GitServiceError
from services.pull_request_service import (
    AutoMergeUnavailableError,
    PullRequestReadyError,
    _classify_checks,
    _derive_status,
    enable_auto_merge,
    get_pull_request_merge_status,
    is_auto_merge_supported,
    merge_pull_request,
    update_pull_request_branch,
)


def _run(status, conclusion=None):
    return {"status": status, "conclusion": conclusion}


@pytest.mark.parametrize(
    "runs, statuses, esperado",
    [
        ([], [], "none"),
        ([_run("completed", "success")], [], "success"),
        ([_run("completed", "skipped"), _run("completed", "neutral")], [], "success"),
        ([_run("in_progress")], [], "pending"),
        ([_run("queued")], [], "pending"),
        ([_run("completed", "failure")], [], "failed"),
        ([_run("completed", "cancelled")], [], "failed"),
        ([_run("completed", "success"), _run("in_progress")], [], "pending"),
        ([_run("completed", "failure"), _run("in_progress")], [], "failed"),
        ([], [{"state": "pending"}], "pending"),
        ([], [{"state": "error"}], "failed"),
        ([_run("completed", "success")], [{"state": "success"}], "success"),
    ],
)
def test_classify_checks(runs, statuses, esperado):
    assert _classify_checks(runs, statuses) == esperado


def _derive(pull, checks="none"):
    chamadas = {"n": 0}

    def load_checks():
        chamadas["n"] += 1
        return checks

    return _derive_status(pull, load_checks), chamadas["n"]


@pytest.mark.parametrize(
    "mergeable_state, esperado",
    [
        ("clean", "ready"),
        ("has_hooks", "ready"),
        ("unstable", "ready"),
        ("dirty", "conflict"),
        ("behind", "behind"),
    ],
)
def test_derive_status_sem_consultar_checks(mergeable_state, esperado):
    status, consultas = _derive({"mergeable_state": mergeable_state})

    assert status["state"] == esperado
    assert consultas == 0  # mergeable_state já responde, poupa chamadas à API


@pytest.mark.parametrize("mergeable_state", ["blocked", "unknown", None])
def test_derive_status_checks_falhos(mergeable_state):
    status, _ = _derive({"mergeable_state": mergeable_state}, checks="failed")
    assert status["state"] == "failed"


@pytest.mark.parametrize("checks", ["pending", "none"])
def test_derive_status_checks_pendentes_ou_ainda_nao_iniciados(checks):
    # Lista vazia logo após o push é corrida, não "ok": conta como pendente.
    status, _ = _derive({"mergeable_state": "blocked"}, checks=checks)
    assert status["state"] == "pending"


def test_derive_status_mergeable_state_ainda_nao_calculado_e_pendente():
    status, _ = _derive({"mergeable_state": None}, checks="success")
    assert status["state"] == "pending"


def test_derive_status_checks_ok_mas_bloqueado_por_regra():
    status, _ = _derive({"mergeable_state": "blocked"}, checks="success")
    assert status["state"] == "blocked"


def test_derive_status_rascunho_e_fechado():
    assert _derive({"draft": True, "mergeable_state": "clean"})[0]["state"] == "blocked"
    assert _derive({"merged": True})[0]["state"] == "closed"
    assert _derive({"state": "closed"})[0]["state"] == "closed"


def test_derive_status_informa_auto_merge_ativo():
    status, _ = _derive({"mergeable_state": "blocked", "auto_merge": {"enabled_by": {}}}, checks="pending")
    assert status["auto_merge"] is True


class _Resp:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


@pytest.fixture
def api(monkeypatch):
    pull_request_service.invalidate_pull_request_status_cache()
    pull_request_service._AUTO_MERGE_SUPPORT.clear()
    monkeypatch.setattr(pull_request_service, "_get_repo_info", lambda repo: ("owner", "repo"))
    monkeypatch.setattr(pull_request_service, "_get_headers", lambda **k: {})
    yield monkeypatch
    pull_request_service.invalidate_pull_request_status_cache()
    pull_request_service._AUTO_MERGE_SUPPORT.clear()


def test_get_pull_request_merge_status_blocked_consulta_checks(api):
    urls = []

    def fake_get(url, **kwargs):
        urls.append(url)
        if url.endswith("/pulls/7"):
            return _Resp({"mergeable_state": "blocked", "head": {"sha": "abc"}})
        if url.endswith("/check-runs"):
            return _Resp({"check_runs": [_run("in_progress")]})
        return _Resp({"statuses": []})

    api.setattr(pull_request_service.requests, "get", fake_get)

    status = get_pull_request_merge_status("/repo", 7)

    assert status["state"] == "pending"
    assert len(urls) == 3


def test_get_pull_request_merge_status_clean_usa_uma_chamada_e_cache(api):
    chamadas = {"n": 0}

    def fake_get(url, **kwargs):
        chamadas["n"] += 1
        return _Resp({"mergeable_state": "clean"})

    api.setattr(pull_request_service.requests, "get", fake_get)

    assert get_pull_request_merge_status("/repo", 7)["state"] == "ready"
    get_pull_request_merge_status("/repo", 7)
    assert chamadas["n"] == 1

    get_pull_request_merge_status("/repo", 7, use_cache=False)
    assert chamadas["n"] == 2


def test_get_pull_request_merge_status_erro_de_rede(api):
    def fake_get(url, **kwargs):
        raise requests.ConnectionError("sem rede")

    api.setattr(pull_request_service.requests, "get", fake_get)

    with pytest.raises(GitServiceError):
        get_pull_request_merge_status("/repo", 7)


def _mock_auto_merge(api, graphql_payload):
    def fake_get(url, **kwargs):
        return _Resp({"node_id": "PR_node"})

    chamadas = {"graphql": 0}

    def fake_post(url, **kwargs):
        chamadas["graphql"] += 1
        return _Resp(graphql_payload)

    api.setattr(pull_request_service.requests, "get", fake_get)
    api.setattr(pull_request_service.requests, "post", fake_post)
    return chamadas


def test_enable_auto_merge_sucesso_guarda_suporte(api):
    _mock_auto_merge(api, {"data": {"enablePullRequestAutoMerge": {"pullRequest": {"number": 7}}}})

    enable_auto_merge("/repo", 7)

    assert is_auto_merge_supported("/repo") is True


def test_enable_auto_merge_desabilitado_no_repo_vira_fallback_e_nao_repete(api):
    chamadas = _mock_auto_merge(
        api, {"errors": [{"message": "Pull request Auto merge is not allowed for this repository"}]}
    )

    with pytest.raises(AutoMergeUnavailableError):
        enable_auto_merge("/repo", 7)

    assert is_auto_merge_supported("/repo") is False

    # Na segunda tentativa nem chama a API: o resultado ficou em cache.
    with pytest.raises(AutoMergeUnavailableError):
        enable_auto_merge("/repo", 8)
    assert chamadas["graphql"] == 1


def test_enable_auto_merge_pr_ja_pronto(api):
    _mock_auto_merge(api, {"errors": [{"message": "Pull request is in clean status"}]})

    with pytest.raises(PullRequestReadyError):
        enable_auto_merge("/repo", 7)

    assert is_auto_merge_supported("/repo") is None  # não diz nada sobre a configuração


def test_enable_auto_merge_branch_sem_protecao_nao_cacheia(api):
    _mock_auto_merge(
        api, {"errors": [{"message": "Pull request Protected branch rules not configured for this branch"}]}
    )

    with pytest.raises(AutoMergeUnavailableError):
        enable_auto_merge("/repo", 7)

    assert is_auto_merge_supported("/repo") is None


def test_enable_auto_merge_outro_erro_e_propagado(api):
    _mock_auto_merge(api, {"errors": [{"message": "algo inesperado"}]})

    with pytest.raises(GitServiceError) as exc_info:
        enable_auto_merge("/repo", 7)

    assert not isinstance(exc_info.value, AutoMergeUnavailableError)


def test_update_pull_request_branch(api):
    api.setattr(
        pull_request_service.requests,
        "put",
        lambda url, **k: _Resp({"message": "Updating pull request branch."}, 202),
    )

    assert "Updating" in update_pull_request_branch("/repo", 7)


@pytest.mark.parametrize(
    "status_code, trecho",
    [(405, "checks obrigatórios"), (403, "Sem permissão"), (404, "Sem permissão"), (409, "conflito")],
)
def test_merge_pull_request_mensagens_por_status(api, status_code, trecho):
    api.setattr(
        pull_request_service.requests,
        "put",
        lambda url, **k: _Resp({"message": "conflito"}, status_code),
    )

    with pytest.raises(GitServiceError) as exc_info:
        merge_pull_request("/repo", 7)

    assert trecho in str(exc_info.value)


def test_merge_pull_request_sucesso_invalida_cache_de_status(api):
    api.setattr(
        pull_request_service.requests,
        "put",
        lambda url, **k: _Resp({"merged": True, "message": "ok", "sha": "abc"}),
    )
    pull_request_service._STATUS_CACHE[("owner", "repo", 7)] = (0, {"state": "ready"})

    result = merge_pull_request("/repo", 7)

    assert result["merged"] is True
    assert pull_request_service._STATUS_CACHE == {}
