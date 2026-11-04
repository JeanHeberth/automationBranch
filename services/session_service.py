import json
import os
import sys
from pathlib import Path

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # sem a dependência o app segue funcionando, guardando o token em arquivo
    keyring = None

    class KeyringError(Exception):
        pass


APP_NAME = "AutomationBranch"
KEYRING_SERVICE = APP_NAME
KEYRING_USER = "github_access_token"


def _app_dir() -> Path:
    """Pasta de dados do app no padrão de cada sistema (macOS, Windows, Linux)."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME

    if sys.platform == "win32":
        base = os.getenv("APPDATA")
        return Path(base) / APP_NAME if base else Path.home() / "AppData" / "Roaming" / APP_NAME

    base = os.getenv("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / APP_NAME


APP_DIR = _app_dir()
SESSION_FILE = APP_DIR / "session.json"


def _default_session() -> dict:
    return {
        "is_authenticated": False,
        "provider": None,
        "display_name": None,
        "email": None,
        "access_token": None,
        "github_login": None,
        "github_id": None,
        "avatar_url": None,
    }


# Cache do token em memória: load_session roda a cada chamada à API do GitHub e cada
# leitura do cofre custa tempo (e pode gerar prompt de acesso no macOS).
_UNSET = object()
_token_cache = _UNSET


def _keyring_get() -> str | None:
    global _token_cache

    if _token_cache is not _UNSET:
        return _token_cache
    if keyring is None:
        return None
    try:
        _token_cache = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except KeyringError:
        return None
    return _token_cache


def _keyring_set(token: str) -> bool:
    """True se o token foi para o cofre do sistema (Keychain, Credential Locker...)."""
    global _token_cache

    if keyring is None:
        return False
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)
    except KeyringError:
        return False
    _token_cache = token
    return True


def _keyring_delete() -> None:
    global _token_cache

    _token_cache = None
    if keyring is None:
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except KeyringError:
        pass  # já não existia ou não há cofre disponível


def _write_session_file(payload: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)

    # 0o600 desde a criação: o token nunca fica legível por outros usuários, nem por um instante.
    descriptor = os.open(SESSION_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    try:
        os.chmod(SESSION_FILE, 0o600)  # arquivo já existente de versões anteriores
    except OSError:
        pass  # Windows: as permissões vêm da pasta do usuário


def load_session() -> dict:
    if not SESSION_FILE.exists():
        return _default_session()

    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return _default_session()

    session = _default_session()
    session.update(data)
    session["is_authenticated"] = bool(session.get("is_authenticated", False))

    file_token = session.get("access_token")
    if file_token:
        # Sessão antiga, com o token em texto puro: migra para o cofre assim que possível.
        if _keyring_set(file_token):
            save_session(session)
    elif session["is_authenticated"]:
        session["access_token"] = _keyring_get()

    return session


def save_session(session_data: dict) -> None:
    payload = _default_session()
    payload.update(session_data)
    payload["is_authenticated"] = bool(payload.get("is_authenticated", False))

    token = payload.get("access_token")
    if token and _keyring_set(token):
        payload["access_token"] = None  # o arquivo guarda só o perfil; o token fica no cofre
    elif not token:
        _keyring_delete()

    _write_session_file(payload)


def clear_session() -> None:
    _keyring_delete()

    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
