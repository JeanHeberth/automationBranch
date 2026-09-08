import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs

import requests

from services.git_runner import GitServiceError


AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
USER_EMAILS_URL = "https://api.github.com/user/emails"


# Portas testadas quando a porta preferida está ocupada. O GitHub aceita
# qualquer porta em redirect URIs de loopback (RFC 8252).
_FALLBACK_PORTS = [8765, 8766, 8767, 8768, 8888]


class _OAuthCallbackServer:
    def __init__(self, preferred_port: int, fallback_ports: Optional[list] = None):
        self.preferred_port = preferred_port
        self.fallback_ports = list(fallback_ports) if fallback_ports is not None else list(_FALLBACK_PORTS)
        self.port: Optional[int] = None
        self.httpd: Optional[HTTPServer] = None
        self.event = threading.Event()
        self.payload = {
            "code": None,
            "state": None,
            "error": None,
        }

    def _candidate_ports(self) -> list:
        seen = []
        for port in [self.preferred_port, *self.fallback_ports]:
            if port and port not in seen:
                seen.append(port)
        return seen

    def start(self):
        payload = self.payload
        event = self.event

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)

                if parsed.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return

                query = parse_qs(parsed.query)
                payload["code"] = query.get("code", [None])[0]
                payload["state"] = query.get("state", [None])[0]
                payload["error"] = query.get("error", [None])[0]

                html = """
                <html>
                  <head><title>Automation Branch</title></head>
                  <body style="font-family: Arial; background:#0f172a; color:#e5e7eb; display:flex; align-items:center; justify-content:center; height:100vh;">
                    <div style="text-align:center;">
                      <h2>Login concluído</h2>
                      <p>Você já pode voltar para o Automation Branch.</p>
                    </div>
                  </body>
                </html>
                """

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))

                event.set()

            def log_message(self, format, *args):
                return

        candidates = self._candidate_ports()
        last_error: Optional[OSError] = None

        for port in candidates:
            try:
                self.httpd = HTTPServer(("127.0.0.1", port), Handler)
                self.port = port
                break
            except OSError as exc:
                last_error = exc

        if self.httpd is None:
            tentadas = ", ".join(str(p) for p in candidates)
            raise GitServiceError(
                "Não foi possível abrir uma porta local para concluir o login do GitHub "
                f"(portas tentadas: {tentadas}). Feche o processo que está usando essas "
                "portas ou defina GITHUB_CALLBACK_PORT com uma porta livre."
            ) from last_error

        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()

    def wait(self, timeout: int = 180) -> dict:
        ok = self.event.wait(timeout)
        if not ok:
            raise GitServiceError("Tempo esgotado aguardando o retorno do login do GitHub.")
        return self.payload

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


def _get_env_config() -> tuple[str, str, int, str]:
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    scopes = os.getenv("GITHUB_OAUTH_SCOPES", "repo user:email").strip()

    if not client_id or not client_secret:
        raise GitServiceError(
            "GITHUB_CLIENT_ID e GITHUB_CLIENT_SECRET precisam estar configurados no ambiente."
        )

    raw_port = os.getenv("GITHUB_CALLBACK_PORT", "8765").strip()
    try:
        callback_port = int(raw_port)
    except ValueError as exc:
        raise GitServiceError(
            f"GITHUB_CALLBACK_PORT inválido: {raw_port!r}. Use um número de porta."
        ) from exc

    return client_id, client_secret, callback_port, scopes


def _pick_primary_email(access_token: str) -> Optional[str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(USER_EMAILS_URL, headers=headers, timeout=15)
    response.raise_for_status()

    emails = response.json()
    if not isinstance(emails, list):
        return None

    for item in emails:
        if item.get("primary") and item.get("verified"):
            return item.get("email")

    for item in emails:
        if item.get("verified"):
            return item.get("email")

    return emails[0].get("email") if emails else None


def authenticate_with_github() -> dict:
    client_id, client_secret, callback_port, scopes = _get_env_config()
    state = secrets.token_urlsafe(32)

    callback_server = _OAuthCallbackServer(callback_port)
    callback_server.start()

    # redirect_uri usa a porta realmente aberta (pode ter caído para uma alternativa).
    redirect_uri = f"http://127.0.0.1:{callback_server.port}/callback"

    try:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
        }
        auth_url = f"{AUTHORIZE_URL}?{urlencode(params)}"

        opened = webbrowser.open(auth_url)
        if not opened:
            raise GitServiceError("Não foi possível abrir o navegador para iniciar o login do GitHub.")

        callback_data = callback_server.wait(timeout=180)

    finally:
        callback_server.stop()

    if callback_data.get("error"):
        raise GitServiceError(f"Login cancelado ou negado no GitHub: {callback_data['error']}")

    code = callback_data.get("code")
    returned_state = callback_data.get("state")

    if not code:
        raise GitServiceError("GitHub não retornou o code de autorização.")

    if returned_state != state:
        raise GitServiceError("Falha de segurança no login: state inválido.")

    token_headers = {
        "Accept": "application/json"
    }
    token_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "state": state,
    }

    token_response = requests.post(
        TOKEN_URL,
        headers=token_headers,
        data=token_payload,
        timeout=15
    )
    token_response.raise_for_status()

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise GitServiceError("GitHub não retornou access_token.")

    user_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }

    user_response = requests.get(USER_URL, headers=user_headers, timeout=15)
    user_response.raise_for_status()
    user_data = user_response.json()

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