import subprocess

# Timeout padrão para comandos Git locais (rápidos).
DEFAULT_TIMEOUT = 30
# Timeout maior para comandos que acessam a rede (pull, push, ls-remote...).
NETWORK_TIMEOUT = 180


class GitServiceError(Exception):
    pass


def run_git_command(
    repo_path: str,
    args: list[str],
    strip: bool = True,
    timeout: float | None = DEFAULT_TIMEOUT,
) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise GitServiceError(
            "Git não encontrado. Verifique se o Git está instalado e disponível no PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise GitServiceError(
            f"O comando Git excedeu o tempo limite de {timeout:g}s e foi interrompido "
            f"(git {' '.join(args)}). Pode ser rede lenta ou o Git aguardando credenciais."
        ) from exc
    except subprocess.CalledProcessError as exc:
        error_message = (
            (exc.stderr or "").strip()
            or (exc.stdout or "").strip()
            or "Erro ao executar comando Git."
        )
        raise GitServiceError(error_message) from exc

    if strip:
        return result.stdout.strip()
    # Preserva espaços à esquerda (essenciais para "status --porcelain"
    # e para a indentação do "log --graph"); remove apenas quebras finais.
    return result.stdout.rstrip("\r\n")
