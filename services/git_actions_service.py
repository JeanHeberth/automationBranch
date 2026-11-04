import os
import re
from typing import Any, Dict, List

from services.branch_delete_service import is_protected
from services.branch_service import get_current_branch, has_upstream
from services.git_runner import NETWORK_TIMEOUT, GitServiceError, run_git_command

REMOTE = "origin"
CLONE_TIMEOUT = 600  # clonar um repositório grande demora mais que um fetch

# Operações que podem parar no meio (conflito) e precisam ser continuadas ou abortadas.
_OPERATION_MARKERS = (
    ("merge", ("MERGE_HEAD",)),
    ("rebase", ("rebase-merge", "rebase-apply")),
    ("cherry-pick", ("CHERRY_PICK_HEAD",)),
    ("revert", ("REVERT_HEAD",)),
)
OPERATION_LABELS = {"merge": "merge", "rebase": "rebase", "cherry-pick": "cherry-pick", "revert": "revert"}


class ConflictError(GitServiceError):
    """A operação parou no meio (conflito ou commit vazio) e ficou em andamento."""

    def __init__(self, message: str, operation: str):
        super().__init__(message)
        self.operation = operation


# ---------- operação em andamento ----------

def _git_dir(repo_path: str) -> str:
    quick = os.path.join(repo_path, ".git")
    if os.path.isdir(quick):
        return quick  # caminho rápido, sem abrir processo
    return run_git_command(repo_path, ["rev-parse", "--absolute-git-dir"])


def get_operation_in_progress(repo_path: str) -> str | None:
    """"merge", "rebase", "cherry-pick", "revert" ou None."""
    try:
        git_dir = _git_dir(repo_path)
    except GitServiceError:
        return None

    for operation, markers in _OPERATION_MARKERS:
        if any(os.path.exists(os.path.join(git_dir, marker)) for marker in markers):
            return operation

    return None


def _run_integration(repo_path: str, args: List[str], timeout: float | None = None) -> str:
    """Roda uma operação que pode conflitar; se parar no meio, levanta ConflictError."""
    kwargs = {} if timeout is None else {"timeout": timeout}

    try:
        return run_git_command(repo_path, args, **kwargs)
    except GitServiceError as exc:
        operation = get_operation_in_progress(repo_path)
        if operation:
            raise ConflictError(str(exc), operation) from exc
        raise


def abort_operation(repo_path: str) -> str:
    operation = get_operation_in_progress(repo_path)
    if not operation:
        raise GitServiceError("Nenhuma operação em andamento para abortar.")

    return run_git_command(repo_path, [operation, "--abort"])


def continue_operation(repo_path: str) -> str:
    """Conclui a operação depois de resolver os conflitos e colocar os arquivos em stage."""
    operation = get_operation_in_progress(repo_path)
    if not operation:
        raise GitServiceError("Nenhuma operação em andamento para continuar.")

    if operation == "merge":
        return _run_integration(repo_path, ["commit", "--no-edit"])

    # core.editor=true: o git não abre o editor para a mensagem do commit.
    return _run_integration(repo_path, ["-c", "core.editor=true", operation, "--continue"])


# ---------- sincronizar / integrar ----------

def fetch_all(repo_path: str) -> str:
    """Busca todos os remotos e limpa referências de branches que não existem mais."""
    run_git_command(repo_path, ["fetch", "--all", "--prune"], timeout=NETWORK_TIMEOUT)
    return "Fetch concluído."


def merge_branch(repo_path: str, branch: str) -> str:
    branch = branch.strip()
    if not branch:
        raise GitServiceError("Informe a branch a ser mesclada.")

    if branch == get_current_branch(repo_path):
        raise GitServiceError("Não dá para mesclar a branch nela mesma.")

    # --no-edit: sem isso o git tentaria abrir um editor para a mensagem do merge commit.
    return _run_integration(repo_path, ["merge", "--no-edit", branch])


def rebase_onto(repo_path: str, branch: str) -> str:
    branch = branch.strip()
    current = get_current_branch(repo_path)

    if not branch:
        raise GitServiceError("Informe a branch de destino do rebase.")
    if branch == current:
        raise GitServiceError("Não dá para fazer rebase de uma branch nela mesma.")
    if is_protected(current):
        raise GitServiceError(f"Não é permitido reescrever o histórico da branch protegida '{current}'.")

    return _run_integration(repo_path, ["rebase", branch])


def _parent_count(repo_path: str, commit: str) -> int:
    line = run_git_command(repo_path, ["rev-list", "--parents", "-n", "1", commit])
    return max(len(line.split()) - 1, 0)


def _check_single_parent(repo_path: str, commit: str, action: str) -> None:
    if _parent_count(repo_path, commit) > 1:
        raise GitServiceError(f"Esse commit é um merge: {action} de merge commit não é suportado.")


def cherry_pick(repo_path: str, commit: str) -> str:
    _check_single_parent(repo_path, commit, "cherry-pick")
    return _run_integration(repo_path, ["cherry-pick", commit])


def revert_commit(repo_path: str, commit: str) -> str:
    _check_single_parent(repo_path, commit, "revert")
    return _run_integration(repo_path, ["revert", "--no-edit", commit])


# ---------- desfazer e recuperar ----------

def get_last_commit_summary(repo_path: str) -> str:
    return run_git_command(repo_path, ["log", "-1", "--pretty=format:%h %s"])


def undo_last_commit(repo_path: str) -> str:
    """Desfaz o último commit mantendo as alterações em stage (git reset --soft HEAD~1)."""
    current = get_current_branch(repo_path)

    if is_protected(current):
        raise GitServiceError(f"Não é permitido reescrever o histórico da branch protegida '{current}'.")

    try:
        run_git_command(repo_path, ["rev-parse", "--verify", "--quiet", "HEAD~1"])
    except GitServiceError as exc:
        raise GitServiceError("Este é o primeiro commit do repositório: não há o que desfazer.") from exc

    summary = get_last_commit_summary(repo_path)
    run_git_command(repo_path, ["reset", "--soft", "HEAD~1"])
    return summary


UNDO_REFLOG_MESSAGE = "reset: moving to HEAD~1"  # o que undo_last_commit deixa no reflog


def get_redo_target(repo_path: str) -> Dict[str, str] | None:
    """O commit que o último "desfazer" removeu, se ainda for possível refazê-lo.

    Só vale logo depois do desfazer: a entrada mais recente do reflog precisa ser o próprio
    `reset --soft HEAD~1`, e o commit removido tem de ser descendente do HEAD atual. Qualquer
    commit, checkout ou outro reset no meio invalida (o Reflog cobre esses casos).
    """
    entries = get_reflog(repo_path, limit=2)
    if len(entries) < 2 or entries[0]["message"] != UNDO_REFLOG_MESSAGE:
        return None

    target = entries[1]["hash"]
    try:
        run_git_command(repo_path, ["merge-base", "--is-ancestor", "HEAD", target])
    except GitServiceError:
        return None

    return {"hash": target, "summary": run_git_command(repo_path, ["log", "-1", "--pretty=format:%h %s", target])}


def redo_last_undo(repo_path: str) -> str:
    """Desfaz o "desfazer": traz de volta o commit removido por `undo_last_commit`."""
    current = get_current_branch(repo_path)

    if is_protected(current):
        raise GitServiceError(f"Não é permitido reescrever o histórico da branch protegida '{current}'.")

    target = get_redo_target(repo_path)
    if target is None:
        raise GitServiceError(
            "Não há um \"desfazer commit\" recente para refazer. "
            "Para voltar a um ponto anterior, use o Reflog."
        )

    # --soft: o stage e os arquivos ficam como estão, nada que você alterou depois é perdido.
    run_git_command(repo_path, ["reset", "--soft", target["hash"]])
    return target["summary"]


def get_reflog(repo_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    output = run_git_command(
        repo_path,
        ["reflog", f"-n{limit}", "--format=%h%x01%gd%x01%gs%x01%cr"],
        strip=False,
    )

    entries = []
    for line in (output or "").splitlines():
        parts = line.split("\x01")
        if len(parts) < 4:
            continue
        entries.append({"hash": parts[0], "selector": parts[1], "message": parts[2], "date": parts[3]})

    return entries


def is_working_tree_clean(repo_path: str) -> bool:
    """Sem alterações em arquivos rastreados (arquivos novos não contam: o reset não os toca)."""
    return not run_git_command(repo_path, ["status", "--porcelain", "--untracked-files=no"]).strip()


def reset_hard(repo_path: str, commit: str) -> str:
    current = get_current_branch(repo_path)

    if is_protected(current):
        raise GitServiceError(f"Não é permitido reescrever o histórico da branch protegida '{current}'.")

    if not is_working_tree_clean(repo_path):
        raise GitServiceError(
            "Há alterações não commitadas, e o reset --hard as perderia. "
            "Faça commit, stash ou descarte-as antes."
        )

    return run_git_command(repo_path, ["reset", "--hard", commit])


# ---------- branches e tags ----------

def validate_ref_name(repo_path: str, name: str, kind: str = "branch") -> str:
    """Valida o nome com as regras do próprio git (git check-ref-format) e o devolve limpo."""
    name = name.strip()
    if not name:
        raise GitServiceError(f"Informe o nome da {kind}.")

    check = ["check-ref-format", "--branch", name] if kind == "branch" else ["check-ref-format", f"refs/tags/{name}"]
    try:
        run_git_command(repo_path, check)
    except GitServiceError as exc:
        raise GitServiceError(f"'{name}' não é um nome de {kind} válido.") from exc

    return name


def create_branch_at(repo_path: str, name: str, commit: str) -> str:
    name = validate_ref_name(repo_path, name, "branch")
    return run_git_command(repo_path, ["branch", name, commit])


def rename_branch(repo_path: str, old_name: str, new_name: str) -> str:
    if is_protected(old_name):
        raise GitServiceError(f"A branch '{old_name}' é protegida e não pode ser renomeada.")

    new_name = validate_ref_name(repo_path, new_name, "branch")
    if new_name == old_name:
        raise GitServiceError("O novo nome é igual ao atual.")

    had_upstream = has_upstream(repo_path, old_name)
    run_git_command(repo_path, ["branch", "-m", old_name, new_name])

    if had_upstream:
        return f"Branch renomeada para '{new_name}'. No remoto ela continua como '{old_name}'."
    return f"Branch renomeada para '{new_name}'."


def list_tags(repo_path: str) -> List[Dict[str, Any]]:
    output = run_git_command(
        repo_path,
        [
            "for-each-ref", "refs/tags", "--sort=-creatordate",
            "--format=%(refname:short)%01%(objecttype)%01%(creatordate:short)%01%(contents:subject)",
        ],
        strip=False,
    )

    tags = []
    for line in (output or "").splitlines():
        parts = line.split("\x01")
        if len(parts) < 4:
            continue
        tags.append(
            {
                "name": parts[0],
                "annotated": parts[1] == "tag",
                "date": parts[2],
                "subject": parts[3],
            }
        )

    return tags


def create_tag(repo_path: str, name: str, message: str = "", commit: str = "HEAD") -> str:
    """Tag anotada se houver mensagem; leve se não houver."""
    name = validate_ref_name(repo_path, name, "tag")
    message = message.strip()

    if message:
        return run_git_command(repo_path, ["tag", "-a", name, "-m", message, commit])
    return run_git_command(repo_path, ["tag", name, commit])


def push_tag(repo_path: str, name: str) -> str:
    return run_git_command(repo_path, ["push", REMOTE, f"refs/tags/{name}"], timeout=NETWORK_TIMEOUT)


def delete_tag(repo_path: str, name: str) -> str:
    return run_git_command(repo_path, ["tag", "-d", name])


def delete_remote_tag(repo_path: str, name: str) -> str:
    return run_git_command(repo_path, ["push", REMOTE, "--delete", f"refs/tags/{name}"], timeout=NETWORK_TIMEOUT)


def get_merged_branches(repo_path: str, base: str) -> List[str]:
    """Branches locais já totalmente mescladas em `base` (exclui protegidas, a atual e a própria base)."""
    output = run_git_command(
        repo_path, ["branch", "--merged", base, "--format=%(refname:short)"]
    )
    current = get_current_branch(repo_path)

    return [
        name for name in (line.strip() for line in output.splitlines())
        if name and name != base and name != current and not is_protected(name)
    ]


# ---------- clonar e inicializar ----------

def repo_name_from_url(url: str) -> str:
    """Nome da pasta que o git usaria: último trecho da URL, sem barra final nem .git."""
    cleaned = url.strip().rstrip("/")
    cleaned = re.sub(r"\.git$", "", cleaned)
    name = re.split(r"[/:\\]", cleaned)[-1]
    return name


def clone_repository(url: str, parent_dir: str) -> str:
    """Clona para `parent_dir/<nome do repositório>` e devolve o caminho."""
    url = url.strip()
    name = repo_name_from_url(url)

    if not url or not name:
        raise GitServiceError("Informe a URL do repositório.")

    if not os.path.isdir(parent_dir):
        raise GitServiceError(f"A pasta de destino não existe: {parent_dir}")

    destination = os.path.join(parent_dir, name)
    if os.path.exists(destination) and os.listdir(destination):
        raise GitServiceError(f"A pasta '{destination}' já existe e não está vazia.")

    run_git_command(parent_dir, ["clone", "--", url, name], timeout=CLONE_TIMEOUT)
    return destination


def init_repository(folder: str) -> str:
    if not os.path.isdir(folder):
        raise GitServiceError(f"A pasta não existe: {folder}")

    if os.path.exists(os.path.join(folder, ".git")):
        raise GitServiceError("Esta pasta já é um repositório Git.")

    run_git_command(folder, ["init"])
    return folder
