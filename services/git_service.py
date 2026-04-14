import subprocess
from typing import List


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


def get_local_branches(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["branch", "--format=%(refname:short)"])
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_current_branch(repo_path: str) -> str:
    output = run_git_command(repo_path, ["branch", "--show-current"])
    return output.strip()


def is_git_repository(repo_path: str) -> bool:
    try:
        output = run_git_command(repo_path, ["rev-parse", "--is-inside-work-tree"])
        return output.strip() == "true"
    except GitServiceError:
        return False


def get_recent_commits(repo_path: str, branch_name: str, limit: int = 15) -> List[str]:
    format_string = "%h | %s | %an"
    output = run_git_command(
        repo_path,
        ["log", branch_name, f"-n{limit}", f"--pretty=format:{format_string}"]
    )

    if not output:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]

def checkout_branch(repo_path: str, branch_name: str) -> str:
    return run_git_command(repo_path, ["checkout", branch_name])