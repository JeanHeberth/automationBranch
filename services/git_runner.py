import subprocess


class GitServiceError(Exception):
    pass


def run_git_command(repo_path: str, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error_message = exc.stderr.strip() or exc.stdout.strip() or "Erro ao executar comando Git."
        raise GitServiceError(error_message) from exc