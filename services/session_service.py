import json
from pathlib import Path


APP_DIR = Path.home() / "Library" / "Application Support" / "AutomationBranch"
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


def load_session() -> dict:
    if not SESSION_FILE.exists():
        return _default_session()

    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        session = _default_session()
        session.update(data)
        session["is_authenticated"] = bool(session.get("is_authenticated", False))
        return session
    except Exception:
        return _default_session()


def save_session(session_data: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)

    payload = _default_session()
    payload.update(session_data)
    payload["is_authenticated"] = bool(payload.get("is_authenticated", False))

    with open(SESSION_FILE, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()