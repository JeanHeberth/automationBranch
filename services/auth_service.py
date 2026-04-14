from services.session_service import load_session, save_session, clear_session


def get_current_session() -> dict:
    return load_session()


def login_with_provider(provider: str) -> dict:
    provider = provider.strip().lower()

    if provider == "github":
        session = {
            "is_authenticated": True,
            "provider": "GitHub",
            "display_name": "GitHub User",
            "email": "github-user@example.com",
        }
    elif provider == "google":
        session = {
            "is_authenticated": True,
            "provider": "Google",
            "display_name": "Google User",
            "email": "google-user@example.com",
        }
    else:
        raise ValueError("Provider inválido.")

    save_session(session)
    return session


def logout() -> None:
    clear_session()