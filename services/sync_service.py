from services.git_runner import run_git_command, GitServiceError, NETWORK_TIMEOUT
from services.branch_service import get_current_branch, has_upstream, get_remotes


def git_pull(repo_path: str) -> str:
    current_branch = get_current_branch(repo_path)

    if has_upstream(repo_path, current_branch):
        return run_git_command(repo_path, ["pull"], timeout=NETWORK_TIMEOUT)

    # Sem upstream configurado: tenta puxar de origin/<branch> se ela existir no remoto.
    if "origin" not in get_remotes(repo_path):
        raise GitServiceError(
            "A branch atual não possui upstream e não há um remote 'origin' configurado."
        )

    remote_head = run_git_command(
        repo_path,
        ["ls-remote", "--heads", "origin", current_branch],
        timeout=NETWORK_TIMEOUT,
    )

    if not remote_head.strip():
        raise GitServiceError(
            f"A branch '{current_branch}' ainda não existe no remoto. "
            "Faça um push primeiro para criá-la."
        )

    return run_git_command(
        repo_path, ["pull", "origin", current_branch], timeout=NETWORK_TIMEOUT
    )


def git_push(repo_path: str) -> str:
    current_branch = get_current_branch(repo_path)

    if has_upstream(repo_path, current_branch):
        return run_git_command(repo_path, ["push"], timeout=NETWORK_TIMEOUT)

    return run_git_command(
        repo_path,
        ["push", "--set-upstream", "origin", current_branch],
        timeout=NETWORK_TIMEOUT,
    )


def git_stash(repo_path: str) -> str:
    return run_git_command(repo_path, ["stash"])


def git_stash_pop(repo_path: str) -> str:
    return run_git_command(repo_path, ["stash", "pop"])
