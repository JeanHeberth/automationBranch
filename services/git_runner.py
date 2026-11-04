import subprocess
import sys

from services.perf import timed

# Timeout padrão para comandos Git locais (rápidos).
DEFAULT_TIMEOUT = 30
# Timeout maior para comandos que acessam a rede (pull, push, ls-remote...).
NETWORK_TIMEOUT = 180


# No Windows, cada subprocess abriria uma janela de console (lento e com "flash" na tela).
_CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class GitServiceError(Exception):
    pass


def run_git_command(
    repo_path: str,
    args: list[str],
    strip: bool = True,
    timeout: float | None = DEFAULT_TIMEOUT,
    ok_returncodes: tuple[int, ...] = (0,),
) -> str:
    """Roda `git -C repo_path <args>`. `ok_returncodes` lista saídas que não são erro
    (ex.: `git grep` sai com 1 quando não encontra nada)."""
    try:
        with timed(f"git {' '.join(args[:3])}"):
            result = subprocess.run(
                ["git", "-C", repo_path, *args],
                capture_output=True,
                text=True,
                # Git emite UTF-8; sem isso o Windows decodifica como cp1252 (mojibake).
                encoding="utf-8",
                errors="replace",
                check=True,
                timeout=timeout,
                creationflags=_CREATIONFLAGS,
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
        if exc.returncode in ok_returncodes:
            return exc.stdout.strip() if strip else exc.stdout.rstrip("\r\n")
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
