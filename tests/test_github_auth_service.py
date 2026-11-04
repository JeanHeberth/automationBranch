import threading

import pytest
import requests

from services import github_auth_service as auth
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


DEVICE = {
    "device_code": "dev123",
    "user_code": "ABCD-1234",
    "verification_uri": "https://github.com/login/device",
    "interval": 0,
    "expires_in": 900,
}


def _script_token_responses(monkeypatch, responses):
    """Faz o POST do token devolver `responses` em sequência."""
    calls = []
    queue = list(responses)

    def fake_post(url, headers=None, data=None, timeout=None):
        calls.append((url, data))
        return FakeResponse(queue.pop(0))

    monkeypatch.setattr(auth.requests, "post", fake_post)
    return calls


# --- configuração ---

def test_config_sem_client_id_aponta_para_o_env(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setattr(auth, "DEFAULT_CLIENT_ID", "")

    with pytest.raises(GitServiceError, match="(?s)GITHUB_CLIENT_ID.*\\.env"):
        auth._get_config()


def test_config_usa_client_id_embutido_sem_nenhuma_variavel(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GITHUB_OAUTH_SCOPES", raising=False)
    monkeypatch.setattr(auth, "DEFAULT_CLIENT_ID", "embutido")

    assert auth._get_config() == ("embutido", "repo user:email")


def test_config_variavel_de_ambiente_sobrescreve_o_embutido(monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_CLIENT_ID", "embutido")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "  outro  ")

    assert auth._get_config()[0] == "outro"


def test_config_escopos_customizados(monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_CLIENT_ID", "embutido")
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", "repo")

    assert auth._get_config() == ("embutido", "repo")


# --- passo 1: código do dispositivo ---

def test_request_device_code_ok(monkeypatch):
    calls = _script_token_responses(monkeypatch, [DEVICE])

    assert auth.request_device_code("cid", "repo") == DEVICE
    assert calls[0][0] == auth.DEVICE_CODE_URL
    assert calls[0][1] == {"client_id": "cid", "scope": "repo"}


def test_request_device_code_flow_desativado(monkeypatch):
    _script_token_responses(monkeypatch, [{"error": "device_flow_disabled"}])

    with pytest.raises(GitServiceError, match="Enable Device Flow"):
        auth.request_device_code("cid", "repo")


def test_request_device_code_resposta_incompleta(monkeypatch):
    _script_token_responses(monkeypatch, [{"device_code": "x"}])

    with pytest.raises(GitServiceError, match="não retornou"):
        auth.request_device_code("cid", "repo")


def test_erro_de_rede_vira_git_service_error(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("sem internet")

    monkeypatch.setattr(auth.requests, "post", boom)

    with pytest.raises(GitServiceError, match="Falha de rede"):
        auth.request_device_code("cid", "repo")


# --- passo 2: aguardar a autorização ---

def test_wait_for_token_aguarda_ate_autorizar(monkeypatch):
    calls = _script_token_responses(
        monkeypatch,
        [{"error": "authorization_pending"}, {"error": "authorization_pending"}, {"access_token": "tok"}],
    )

    assert auth.wait_for_token("cid", DEVICE) == "tok"
    assert len(calls) == 3
    assert calls[0][1]["grant_type"] == auth.DEVICE_GRANT_TYPE
    assert calls[0][1]["device_code"] == "dev123"
    assert "client_secret" not in calls[0][1]


def test_wait_for_token_slow_down_aumenta_o_intervalo(monkeypatch):
    waits = []

    class RecordingEvent(threading.Event):
        def wait(self, timeout=None):
            waits.append(timeout)
            return False

    _script_token_responses(
        monkeypatch,
        [{"error": "slow_down", "interval": 7}, {"access_token": "tok"}],
    )

    auth.wait_for_token("cid", DEVICE, RecordingEvent())

    assert waits == [0.0, 7.0]


@pytest.mark.parametrize(
    "error, mensagem",
    [
        ("access_denied", "negado"),
        ("expired_token", "expirou"),
        ("device_flow_disabled", "Enable Device Flow"),
        ("incorrect_client_credentials", "incorrect_client_credentials"),
    ],
)
def test_wait_for_token_erros_terminais(monkeypatch, error, mensagem):
    _script_token_responses(monkeypatch, [{"error": error}])

    with pytest.raises(GitServiceError, match=mensagem):
        auth.wait_for_token("cid", DEVICE)


def test_wait_for_token_cancelado_nao_consulta_o_github(monkeypatch):
    calls = _script_token_responses(monkeypatch, [])
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(GitServiceError, match="cancelado"):
        auth.wait_for_token("cid", {**DEVICE, "interval": 5}, cancel)

    assert calls == []


def test_wait_for_token_codigo_expirado_pelo_prazo(monkeypatch):
    calls = _script_token_responses(monkeypatch, [])

    with pytest.raises(GitServiceError, match="expirou"):
        auth.wait_for_token("cid", {**DEVICE, "expires_in": -1})

    assert calls == []


# --- passo 3: sessão ---

def test_fetch_session_usa_email_primario_quando_perfil_nao_tem(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer tok"
        if url == auth.USER_URL:
            return FakeResponse({"login": "jean", "name": None, "id": 7, "avatar_url": "u", "email": None})
        return FakeResponse([
            {"email": "b@x.com", "verified": True, "primary": False},
            {"email": "a@x.com", "verified": True, "primary": True},
        ])

    monkeypatch.setattr(auth.requests, "get", fake_get)

    session = auth.fetch_session("tok")

    assert session["is_authenticated"] is True
    assert session["provider"] == "GitHub"
    assert session["display_name"] == "jean"
    assert session["email"] == "a@x.com"
    assert session["access_token"] == "tok"
    assert session["github_id"] == 7


def test_fetch_session_segue_sem_email_se_a_consulta_falhar(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        if url == auth.USER_URL:
            return FakeResponse({"login": "jean", "email": None})
        raise requests.ConnectionError("x")

    monkeypatch.setattr(auth.requests, "get", fake_get)

    assert auth.fetch_session("tok")["email"] is None


# --- fluxo completo ---

def test_authenticate_entrega_o_codigo_antes_de_aguardar(monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_CLIENT_ID", "cid")
    order = []

    def fake_post(url, headers=None, data=None, timeout=None):
        if url == auth.DEVICE_CODE_URL:
            order.append("device")
            return FakeResponse(DEVICE)
        order.append("poll")
        return FakeResponse({"access_token": "tok"})

    monkeypatch.setattr(auth.requests, "post", fake_post)
    monkeypatch.setattr(
        auth.requests, "get",
        lambda url, headers=None, timeout=None: FakeResponse({"login": "jean", "email": "j@x.com"}),
    )

    session = auth.authenticate_with_github(lambda device: order.append(device["user_code"]))

    assert order == ["device", "ABCD-1234", "poll"]
    assert session["display_name"] == "jean"
