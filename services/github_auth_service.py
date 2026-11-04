import os
import threading
import time
from typing import Callable, Optional

import requests

from services.git_runner import GitServiceError


DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
USER_EMAILS_URL = "https://api.github.com/user/emails"

DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
DEFAULT_SCOPES = "repo user:email"
REQUEST_TIMEOUT = 15

# O Client ID vem de GITHUB_CLIENT_ID (.env). Não é segredo: o Device Flow não usa client_secret
# e o ID só identifica o OAuth App na tela de autorização. DEFAULT_CLIENT_ID permite embuti-lo
# no código numa distribuição futura; a variável de ambiente sempre tem prioridade.
DEFAULT_CLIENT_ID = ""

# O Device Flow não usa client_secret nem callback local: o app mostra um código, o usuário o
# digita em github.com/login/device e o app consulta o GitHub até a autorização sair.
# https://docs.github.com/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow


def _get_config() -> tuple[str, str]:
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip() or DEFAULT_CLIENT_ID
    scopes = os.getenv("GITHUB_OAUTH_SCOPES", DEFAULT_SCOPES).strip() or DEFAULT_SCOPES

    if not client_id:
        raise GitServiceError(
            "GITHUB_CLIENT_ID não está configurado.\n\n"
            "Crie um OAuth App no GitHub (com 'Enable Device Flow' marcado), copie o Client ID "
            "e coloque no arquivo .env na raiz do projeto:\n"
            "GITHUB_CLIENT_ID=seu_client_id\n\n"
            "Depois reinicie o app. Passo a passo no README, seção 'Login com GitHub'."
        )

    return client_id, scopes


def _post_json(url: str, data: dict) -> dict:
    try:
        response = requests.post(
            url,
            headers={"Accept": "application/json"},
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise GitServiceError(f"Falha de rede ao falar com o GitHub: {exc}") from exc
    except ValueError as exc:
        raise GitServiceError("Resposta inválida do GitHub.") from exc


def _get_json(url: str, access_token: str):
    try:
        response = requests.get(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise GitServiceError(f"Falha de rede ao falar com o GitHub: {exc}") from exc
    except ValueError as exc:
        raise GitServiceError("Resposta inválida do GitHub.") from exc


def request_device_code(client_id: str, scopes: str) -> dict:
    """Passo 1: pede ao GitHub um código para o usuário digitar no navegador."""
    data = _post_json(DEVICE_CODE_URL, {"client_id": client_id, "scope": scopes})

    if data.get("error") == "device_flow_disabled":
        raise GitServiceError(
            "O Device Flow está desativado neste OAuth App. "
            "Marque 'Enable Device Flow' nas configurações do app no GitHub."
        )

    if data.get("error"):
        raise GitServiceError(
            f"GitHub recusou o início do login: {data.get('error_description') or data['error']}"
        )

    if not all(data.get(key) for key in ("device_code", "user_code", "verification_uri")):
        raise GitServiceError("GitHub não retornou o código de autorização.")

    return data


def wait_for_token(client_id: str, device: dict, cancel: Optional[threading.Event] = None) -> str:
    """Passo 2: consulta o GitHub no intervalo pedido até o usuário autorizar, negar ou expirar."""
    cancel = cancel or threading.Event()
    interval = float(device.get("interval", 5))
    deadline = time.monotonic() + float(device.get("expires_in", 900))

    while True:
        # wait() acorda na hora se o usuário cancelar; devolve True nesse caso.
        if cancel.wait(interval):
            raise GitServiceError("Login cancelado.")

        if time.monotonic() > deadline:
            raise GitServiceError("O código expirou. Inicie o login novamente.")

        data = _post_json(
            TOKEN_URL,
            {
                "client_id": client_id,
                "device_code": device["device_code"],
                "grant_type": DEVICE_GRANT_TYPE,
            },
        )

        token = data.get("access_token")
        if token:
            return token

        error = data.get("error")

        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval = float(data.get("interval", interval + 5))
            continue
        if error == "expired_token":
            raise GitServiceError("O código expirou. Inicie o login novamente.")
        if error == "access_denied":
            raise GitServiceError("Login negado no GitHub.")
        if error == "device_flow_disabled":
            raise GitServiceError(
                "O Device Flow está desativado neste OAuth App. "
                "Marque 'Enable Device Flow' nas configurações do app no GitHub."
            )

        raise GitServiceError(
            f"Falha no login do GitHub: {data.get('error_description') or error or 'resposta inesperada'}"
        )


def _pick_primary_email(access_token: str) -> Optional[str]:
    emails = _get_json(USER_EMAILS_URL, access_token)
    if not isinstance(emails, list):
        return None

    for item in emails:
        if item.get("primary") and item.get("verified"):
            return item.get("email")

    for item in emails:
        if item.get("verified"):
            return item.get("email")

    return emails[0].get("email") if emails else None


def fetch_session(access_token: str) -> dict:
    """Passo 3: monta a sessão do app a partir do token."""
    user_data = _get_json(USER_URL, access_token)

    email = user_data.get("email")
    if not email:
        try:
            email = _pick_primary_email(access_token)
        except Exception:
            email = None

    return {
        "is_authenticated": True,
        "provider": "GitHub",
        "display_name": user_data.get("name") or user_data.get("login") or "GitHub User",
        "email": email,
        "access_token": access_token,
        "github_login": user_data.get("login"),
        "github_id": user_data.get("id"),
        "avatar_url": user_data.get("avatar_url"),
    }


def authenticate_with_github(
    on_code: Callable[[dict], None],
    cancel: Optional[threading.Event] = None,
) -> dict:
    """Login completo. `on_code(device)` recebe `user_code` e `verification_uri` para a UI exibir."""
    client_id, scopes = _get_config()

    device = request_device_code(client_id, scopes)
    on_code(device)

    access_token = wait_for_token(client_id, device, cancel)
    return fetch_session(access_token)
