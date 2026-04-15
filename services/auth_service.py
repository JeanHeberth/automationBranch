from services.github_auth_service import authenticate_with_github
from services.session_service import load_session, save_session, clear_session


def get_current_session() -> dict:
    return load_session()


def login_with_github() -> dict:
    session = authenticate_with_github()
    save_session(session)
    return session


def login_with_google() -> dict:
    raise NotImplementedError("Login com Google ainda não foi implementado.")


def logout() -> None:
    clear_session()