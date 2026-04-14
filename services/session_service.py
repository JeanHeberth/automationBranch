import json
from pathlib import Path


SESSION_FILE = Path(".session.json")


def load_session() -> dict:
    if not SESSION_FILE.exists():
        return {
            "is_authenticated": False,
            "provider": None,
            "display_name": None,
            "email": None,
        }

    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            "is_authenticated": bool(data.get("is_authenticated", False)),
            "provider": data.get("provider"),
            "display_name": data.get("display_name"),
            "email": data.get("email"),
        }
    except Exception:
        return {
            "is_authenticated": False,
            "provider": None,
            "display_name": None,
            "email": None,
        }


def save_session(session_data: dict) -> None:
    payload = {
        "is_authenticated": bool(session_data.get("is_authenticated", False)),
        "provider": session_data.get("provider"),
        "display_name": session_data.get("display_name"),
        "email": session_data.get("email"),
    }

    with open(SESSION_FILE, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()