import threading
from typing import Callable, Optional

from services.github_auth_service import authenticate_with_github
from services.session_service import load_session, save_session, clear_session


def get_current_session() -> dict:
    return load_session()


def login_with_github(
    on_code: Callable[[dict], None],
    cancel: Optional[threading.Event] = None,
) -> dict:
    session = authenticate_with_github(on_code, cancel)
    save_session(session)
    return session


def logout() -> None:
    clear_session()
