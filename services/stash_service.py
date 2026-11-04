import re
from typing import Any, Dict, List

from services.commit_service import _rename_origins
from services.git_runner import GitServiceError, run_git_command

_SUBJECT_RE = re.compile(r"^(?:WIP on|On) ([^:]+): (.*)$")


def list_stashes(repo_path: str) -> List[Dict[str, Any]]:
    output = run_git_command(
        repo_path,
        ["stash", "list", "--format=%gd%x01%gs%x01%cr"],
        strip=False,
    )

    stashes: List[Dict[str, Any]] = []

    for line in (output or "").splitlines():
        parts = line.split("\x01")
        if len(parts) < 3:
            continue

        ref, subject, when = parts[0], parts[1], parts[2]
        match = _SUBJECT_RE.match(subject)
        branch, message = (match.group(1), match.group(2)) if match else ("", subject)

        stashes.append({"ref": ref, "message": message, "branch": branch, "date": when})

    return stashes


def stash_changes(repo_path: str, message: str = "", paths: List[str] | None = None) -> str:
    """Guarda alterações em um stash (inclui arquivos novos).

    Com `paths`, só esses arquivos; sem, tudo. Levanta erro se não havia nada a guardar.
    """
    args = ["stash", "push", "--include-untracked"]

    clean_message = message.strip()
    if clean_message:
        args += ["-m", clean_message]

    if paths is not None:
        if not paths:
            raise GitServiceError("Selecione ao menos um arquivo para o stash.")
        origins = _rename_origins(repo_path, paths)
        targets = list(dict.fromkeys(paths + origins))
        if origins:
            # O git não casa a origem de um rename em stage como pathspec do stash (e o pop
            # depois conflita). Fora do stage, origem vira "apagado" e destino "novo": casam.
            run_git_command(repo_path, ["reset", "-q", "--", *targets])
        args += ["--", *targets]

    output = run_git_command(repo_path, args)

    # O git sai com sucesso (código 0) mesmo quando não havia o que guardar.
    if "No local changes to save" in output:
        raise GitServiceError("Não há alterações para guardar em stash.")

    return output


def apply_stash(repo_path: str, ref: str, drop: bool = False) -> str:
    """Reaplica o stash. Com `drop`, remove-o em caso de sucesso (git stash pop).

    Em conflito o git mantém o stash e o erro é levantado; os arquivos ficam com marcadores.
    """
    return run_git_command(repo_path, ["stash", "pop" if drop else "apply", ref])


def drop_stash(repo_path: str, ref: str) -> str:
    return run_git_command(repo_path, ["stash", "drop", ref])


def get_stash_diff(repo_path: str, ref: str) -> str:
    try:
        diff = run_git_command(repo_path, ["stash", "show", "-p", "--include-untracked", ref], strip=False)
    except GitServiceError:
        # Git antigo (< 2.32) não tem --include-untracked no "stash show".
        diff = run_git_command(repo_path, ["stash", "show", "-p", ref], strip=False)

    return diff if diff.strip() else "(sem diferenças)"
