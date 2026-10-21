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


def get_remote_branches(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["branch", "-r", "--format=%(refname:short)"])
    if not output:
        return []

    branches = []
    for line in output.splitlines():
        branch = line.strip()
        # Ignora linhas vazias, o ponteiro simbólico (ex.: "origin/HEAD -> origin/main")
        # e o próprio "origin" que o %(refname:short) gera para refs/remotes/origin/HEAD.
        if not branch or "->" in branch or "/" not in branch:
            continue
        branches.append(branch)

    return branches


def get_local_and_remote_branches(repo_path: str) -> tuple[List[str], List[str]]:
    """Local e remotas num único processo git (equivale a get_local_branches + get_remote_branches)."""
    output = run_git_command(
        repo_path,
        ["for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes"],
    )

    local: List[str] = []
    remote: List[str] = []

    for line in output.splitlines():
        ref = line.strip()
        if ref.startswith("refs/heads/"):
            local.append(ref[len("refs/heads/"):])
        elif ref.startswith("refs/remotes/"):
            name = ref[len("refs/remotes/"):]
            # Ignora o ponteiro simbólico origin/HEAD (mesmo critério de get_remote_branches).
            if "/" not in name or name.endswith("/HEAD"):
                continue
            remote.append(name)

    return local, remote


def get_remotes(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["remote"])
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_origin_remote_url(repo_path: str) -> str:
    try:
        return run_git_command(repo_path, ["remote", "get-url", "origin"]).strip()
    except GitServiceError:
        return ""


def is_detached_head(repo_path: str) -> bool:
    try:
        run_git_command(repo_path, ["symbolic-ref", "-q", "HEAD"])
        return False
    except GitServiceError:
        return True


def get_current_branch(repo_path: str) -> str:
    output = run_git_command(repo_path, ["branch", "--show-current"]).strip()
    if output:
        return output

    # Detached HEAD (ou repositório sem commits): "--show-current" volta vazio.
    # Usa o hash abreviado, que continua sendo uma revisão válida para "git log".
    try:
        return run_git_command(repo_path, ["rev-parse", "--short", "HEAD"]).strip()
    except GitServiceError:
        return ""


def checkout_branch(repo_path: str, branch_name: str) -> str:
    return run_git_command(repo_path, ["checkout", branch_name])


def create_branch(repo_path: str, branch_name: str) -> str:
    branch_name = branch_name.strip()

    if not branch_name:
        raise ValueError("Nome da branch não pode ser vazio.")

    branch_name = branch_name.lower().replace(" ", "-")

    valid_prefixes = ("feature/", "bugfix/", "hotfix/", "release/")

    if not branch_name.startswith(valid_prefixes):
        branch_name = f"feature/{branch_name}"

    return run_git_command(repo_path, ["checkout", "-b", branch_name])


def has_upstream(repo_path: str, branch_name: str) -> bool:
    try:
        output = run_git_command(
            repo_path,
            ["rev-parse", "--abbrev-ref", f"{branch_name}@{{upstream}}"]
        )
        return bool(output.strip())
    except GitServiceError:
        return False

