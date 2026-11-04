import pytest
import requests

from services import pull_request_service as prs
from services.git_runner import GitServiceError


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


def _api_pr(number, title, head, state="open", merged_at=None, user="jean", base="main"):
    return {
        "number": number, "title": title, "state": state, "merged_at": merged_at,
        "html_url": f"https://github.com/o/r/pull/{number}",
        "head": {"ref": head}, "base": {"ref": base}, "user": {"login": user},
    }


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    prs._ALL_PR_CACHE.clear()
    monkeypatch.setattr(prs, "_get_repo_info", lambda repo_path: ("o", "r"))
    monkeypatch.setattr(prs, "_get_headers", lambda require_token=False: {})


SAMPLE = [
    {"number": 12, "title": "Adiciona busca", "head": "feature/busca", "base": "main", "state": "merged", "author": "ana", "url": "u12"},
    {"number": 50, "title": "Corrige login", "head": "feature/login", "base": "develop", "state": "open", "author": "jean", "url": "u50"},
    {"number": 7, "title": "Ajusta busca de commits", "head": "fix/busca-commits", "base": "main", "state": "closed", "author": "jean", "url": "u7"},
]


def test_list_pull_requests_classifica_estados_e_pede_todos(monkeypatch):
    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append((url, params))
        return FakeResponse([
            _api_pr(3, "aberto", "a"),
            _api_pr(2, "mergeado", "b", state="closed", merged_at="2026-01-01T00:00:00Z"),
            _api_pr(1, "fechado", "c", state="closed"),
        ])

    monkeypatch.setattr(prs.requests, "get", fake_get)

    result = prs.list_pull_requests("repo")

    assert [(p["number"], p["state"]) for p in result] == [(3, "open"), (2, "merged"), (1, "closed")]
    assert result[0]["author"] == "jean" and result[0]["head"] == "a" and result[0]["base"] == "main"
    assert calls[0][1]["state"] == "all" and calls[0][1]["per_page"] == 100


def test_list_pull_requests_usa_cache(monkeypatch):
    count = []
    monkeypatch.setattr(prs.requests, "get", lambda *a, **k: (count.append(1), FakeResponse([_api_pr(1, "x", "a")]))[1])

    prs.list_pull_requests("repo")
    prs.list_pull_requests("repo")
    assert len(count) == 1

    prs.list_pull_requests("repo", use_cache=False)
    assert len(count) == 2


def test_list_pull_requests_erro_de_rede(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(prs.requests, "get", boom)

    with pytest.raises(GitServiceError, match="Erro ao listar"):
        prs.list_pull_requests("repo")


def test_get_pull_request_existente_e_inexistente(monkeypatch):
    monkeypatch.setattr(prs.requests, "get", lambda *a, **k: FakeResponse(_api_pr(99, "antigo", "x", state="closed")))
    assert prs.get_pull_request("repo", 99)["number"] == 99

    monkeypatch.setattr(prs.requests, "get", lambda *a, **k: FakeResponse({}, status=404))
    assert prs.get_pull_request("repo", 12345) is None


@pytest.mark.parametrize("texto, numero", [("12", 12), ("#12", 12), ("  #7 ", 7), ("12a", None), ("busca", None), ("", None)])
def test_parse_pull_request_number(texto, numero):
    assert prs.parse_pull_request_number(texto) == numero


def test_filter_por_numero_exato():
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "#12")] == [12]
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "50")] == [50]


def test_filter_por_titulo_branch_e_autor_com_abertos_primeiro():
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "busca")] == [12, 7]   # merged antes de closed
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "feature/login")] == [50]
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "JEAN")] == [50, 7]    # open antes de closed
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "develop")] == [50]    # branch de destino


def test_filter_todas_as_palavras_e_sem_resultado():
    assert [p["number"] for p in prs.filter_pull_requests(SAMPLE, "busca commits")] == [7]
    assert prs.filter_pull_requests(SAMPLE, "inexistente") == []
    assert prs.filter_pull_requests(SAMPLE, "   ") == []


def test_filter_numero_fora_da_lista_cai_na_busca_por_texto():
    assert prs.filter_pull_requests(SAMPLE, "999") == []
