from services.git_runner import run_git_command
from services.branch_service import get_current_branch, has_upstream


def git_pull(repo_path: str) -> str:
    return run_git_command(repo_path, ["pull"])


def git_push(repo_path: str) -> str:
    current_branch = get_current_branch(repo_path)

    if has_upstream(repo_path, current_branch):
        return run_git_command(repo_path, ["push"])

    return run_git_command(
        repo_path,
        ["push", "--set-upstream", "origin", current_branch]
    )


def git_stash(repo_path: str) -> str:
    return run_git_command(repo_path, ["stash"])


def git_stash_pop(repo_path: str) -> str:
    return run_git_command(repo_path, ["stash", "pop"])