from typing import List

from services.git_runner import run_git_command, GitServiceError


def is_git_repository(repo_path: str) -> bool:
    try:
        output = run_git_command(repo_path, ["rev-parse", "--is-inside-work-tree"])
        return output.strip() == "true"
    except GitServiceError:
        return False


def get_local_branches(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["branch", "--format=%(refname:short)"])
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_current_branch(repo_path: str) -> str:
    output = run_git_command(repo_path, ["branch", "--show-current"])
    return output.strip()


def checkout_branch(repo_path: str, branch_name: str) -> str:
    return run_git_command(repo_path, ["checkout", branch_name])


def create_branch(repo_path: str, branch_name: str) -> str:
    return run_git_command(repo_path, ["checkout", "-b", branch_name])