from services.git_runner import run_git_command


def git_pull(repo_path: str) -> str:
    return run_git_command(repo_path, ["pull"])


def git_push(repo_path: str) -> str:
    return run_git_command(repo_path, ["push"])


def git_stash(repo_path: str) -> str:
    return run_git_command(repo_path, ["stash"])


def git_stash_pop(repo_path: str) -> str:
    return run_git_command(repo_path, ["stash", "pop"])