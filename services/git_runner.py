import subprocess


class GitServiceError(Exception):
    pass


def run_git_command(repo_path: str, args: list[str], strip: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True,
            text=True,
            check=True
        )
        if strip:
            return result.stdout.strip()
        # Preserva espaços à esquerda (essenciais para "status --porcelain"
        # e para a indentação do "log --graph"); remove apenas quebras finais.
        return result.stdout.rstrip("\r\n")
    except subprocess.CalledProcessError as exc:
        error_message = exc.stderr.strip() or exc.stdout.strip() or "Erro ao executar comando Git."
        raise GitServiceError(error_message) from exc
