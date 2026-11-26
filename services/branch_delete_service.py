from services.git_runner import run_git_command, GitServiceError
from services.branch_service import get_local_branches, get_remote_branches, get_current_branch

PROTECTED_BRANCHES = {"main", "master", "develop", "developer"}


def normalize_branch_name(branch_name: str) -> str:
    return branch_name.strip()


def is_protected(branch_name: str) -> bool:
    return normalize_branch_name(branch_name).lower() in PROTECTED_BRANCHES


def filter_deletable(branches: list[str]) -> list[str]:
    return [b for b in branches if b and not is_protected(b)]


def get_protected_remote_branches(repo_path: str, exclude: str | None = None) -> list[str]:
    """Branches protegidas existentes no remote, candidatas a base de um PR.

    Ordena na ordem de PROTECTED_BRANCHES e cai para ["main"] se nenhuma for encontrada.
    """
    ordem = ["main", "master", "develop", "developer"]
    nomes = {b.split("/", 1)[1] for b in get_remote_branches(repo_path) if "/" in b}
    protegidas = [b for b in ordem if b in nomes and b != exclude]
    return protegidas or [b for b in ["main"] if b != exclude]


def get_pr_base_branch(repo_path: str, current_branch: str) -> str:
    """Base única de um PR, pelo fluxo develop -> main: de qualquer branch o PR vai para
    a develop; da própria develop vai para a main. Impede abrir PR direto na main.

    Só vale se a base existir no remote; senão levanta ValueError dizendo qual falta.
    """
    nomes = {b.split("/", 1)[1] for b in get_remote_branches(repo_path) if "/" in b}

    if current_branch.strip().lower() in ("develop", "developer"):
        candidatas = ["main", "master"]
    else:
        candidatas = ["develop", "developer"]

    for base in candidatas:
        if base in nomes:
            return base

    raise ValueError(
        f"A branch '{candidatas[0]}' não existe no remote; ela é a base do PR a partir de "
        f"'{current_branch}'. Envie-a (push) ao remote antes de abrir o PR."
    )


def get_deletable_local_branches(repo_path: str) -> list[str]:
    current_branch = get_current_branch(repo_path)
    branches = get_local_branches(repo_path)

    deletable = []
    for branch in branches:
        if branch == current_branch:
            continue
        if is_protected(branch):
            continue
        deletable.append(branch)

    return deletable


def get_deletable_remote_branches(repo_path: str) -> list[str]:
    branches = get_remote_branches(repo_path)
    cleaned = []

    for branch in branches:
        if not branch:
            continue

        if "->" in branch:
            continue

        # A deleção sempre empurra para o origin: branches de outros remotes ficam de fora.
        if not branch.startswith("origin/"):
            continue
        branch = branch[len("origin/"):]

        if is_protected(branch):
            continue

        cleaned.append(branch)

    return cleaned


def delete_local_branch(repo_path: str, branch_name: str) -> str:
    branch_name = normalize_branch_name(branch_name)

    if not branch_name:
        raise GitServiceError("Informe o nome da branch.")

    if is_protected(branch_name):
        raise GitServiceError(f"A branch '{branch_name}' é protegida e não pode ser deletada.")

    current_branch = get_current_branch(repo_path)
    if branch_name == current_branch:
        raise GitServiceError("Não é permitido deletar a branch atual.")

    return run_git_command(repo_path, ["branch", "-D", branch_name])


def delete_remote_branch(repo_path: str, branch_name: str) -> str:
    branch_name = normalize_branch_name(branch_name)

    if not branch_name:
        raise GitServiceError("Informe o nome da branch.")

    if is_protected(branch_name):
        raise GitServiceError(f"A branch '{branch_name}' é protegida e não pode ser deletada.")

    return run_git_command(repo_path, ["push", "origin", "--delete", branch_name])


def delete_all_local(repo_path: str) -> list[str]:
    branches = get_deletable_local_branches(repo_path)
    results = []

    for branch in branches:
        try:
            result = delete_local_branch(repo_path, branch)
            results.append(result if result else f"Branch local deletada: {branch}")
        except Exception as exc:
            results.append(f"Falha ao deletar local '{branch}': {str(exc)}")

    return results


def delete_all_remote(repo_path: str) -> list[str]:
    branches = get_deletable_remote_branches(repo_path)
    results = []

    for branch in branches:
        try:
            result = delete_remote_branch(repo_path, branch)
            results.append(result if result else f"Branch remota deletada: {branch}")
        except Exception as exc:
            results.append(f"Falha ao deletar remota '{branch}': {str(exc)}")

    return results