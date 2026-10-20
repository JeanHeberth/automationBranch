import socket

import pytest

from services import github_auth_service as auth
from services.git_runner import GitServiceError


def _porta_ocupada():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen()
    return s, s.getsockname()[1]


def _porta_livre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


def test_callback_server_usa_porta_preferida_quando_livre():
    porta = _porta_livre()
    srv = auth._OAuthCallbackServer(porta, fallback_ports=[])
    srv.start()
    try:
        assert srv.port == porta
        assert srv.httpd is not None
    finally:
        srv.stop()


def test_callback_server_pula_porta_ocupada():
    ocupada_sock, ocupada = _porta_ocupada()
    livre = _porta_livre()
    try:
        srv = auth._OAuthCallbackServer(ocupada, fallback_ports=[livre])
        srv.start()
        try:
            assert srv.port == livre
        finally:
            srv.stop()
    finally:
        ocupada_sock.close()


def test_callback_server_sem_porta_disponivel():
    ocupada_sock, ocupada = _porta_ocupada()
    try:
        srv = auth._OAuthCallbackServer(ocupada, fallback_ports=[ocupada])
        with pytest.raises(GitServiceError, match="porta local"):
            srv.start()
    finally:
        ocupada_sock.close()


def test_get_env_config_exige_client_id(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    with pytest.raises(GitServiceError, match="GITHUB_CLIENT_ID"):
        auth._get_env_config()


def test_get_env_config_porta_invalida(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GITHUB_CALLBACK_PORT", "abc")
    with pytest.raises(GitServiceError, match="GITHUB_CALLBACK_PORT"):
        auth._get_env_config()


def test_get_env_config_ok(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.delenv("GITHUB_CALLBACK_PORT", raising=False)
    client_id, client_secret, port, scopes = auth._get_env_config()
    assert (client_id, client_secret, port) == ("id", "secret", 8765)
    assert "repo" in scopes
