import re
from typing import List, Dict, Any

from services.branch_service import has_upstream
from services.git_runner import run_git_command, GitServiceError


def get_recent_commit_rows(repo_path: str, branch_name: str, limit: int = 25) -> List[Dict[str, Any]]:
    output = run_git_command(
        repo_path,
        [
            "log",
            branch_name,
            "--graph",
            "--decorate=short",
            f"-n{limit}",
            "--pretty=format:%h%x01%s%x01%an%x01%P%x01%d",
        ],
        strip=False,
    )

    if not output:
        return []

    rows: List[Dict[str, Any]] = []

    for raw_line in output.splitlines():
        if "\x01" not in raw_line:
            continue

        before, rest = raw_line.split("\x01", 1)
        before = before.rstrip()

        match = re.match(r"^(.*?)([0-9a-fA-F]+)$", before)
        if not match:
            continue

        graph_prefix = match.group(1)
        commit_hash = match.group(2)

        parts = rest.split("\x01")
        subject = parts[0].strip() if len(parts) > 0 else ""
        author = parts[1].strip() if len(parts) > 1 else ""
        parents_field = parts[2].strip() if len(parts) > 2 else ""
        decorations = parts[3].strip() if len(parts) > 3 else ""

        parents = [p for p in parents_field.split() if p]

        rows.append(
            {
                "graph": graph_prefix,
                "hash": commit_hash,
                "subject": subject,
                "author": author,
                "parents": parents,
                "decorations": decorations,
                "is_merge": len(parents) > 1,
            }
        )

    return rows


def _parse_status_path(raw: str) -> str:
    # Formato do "git status --short": "XY <caminho>" (caminho a partir da coluna 3).
    # Em renomeações vem "R  origem -> destino"; mostramos o destino.
    file_path = raw[3:].strip() if len(raw) > 3 else raw.strip()
    if " -> " in file_path:
        file_path = file_path.split(" -> ", 1)[1]
    return file_path


def get_changed_files(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["status", "--short"], strip=False)

    if not output:
        return []

    files = []
    for line in output.splitlines():
        if not line.strip():
            continue

        status = line[:2]
        file_path = _parse_status_path(line)
        files.append(f"{status} | {file_path}")

    return files


def get_changed_files_grouped(repo_path: str) -> Dict[str, List[str]]:
    output = run_git_command(repo_path, ["status", "--short"], strip=False)

    grouped = {
        "staged": [],
        "unstaged": [],
    }

    if not output:
        return grouped

    for line in output.splitlines():
        if not line.strip() or len(line) < 3:
            continue

        index_status = line[0]
        worktree_status = line[1]
        file_path = _parse_status_path(line)

        # "?" = arquivo não rastreado: não está em stage, só aparece como unstaged.
        if index_status not in (" ", "?"):
            grouped["staged"].append(f"{index_status} | {file_path}")

        if worktree_status != " ":
            grouped["unstaged"].append(f"{worktree_status} | {file_path}")

    return grouped


def stage_all_changes(repo_path: str) -> str:
    return run_git_command(repo_path, ["add", "-A"])


def commit_all_changes(repo_path: str, message: str) -> str:
    clean_message = message.strip()

    if not clean_message:
        raise GitServiceError("A mensagem de commit não pode estar vazia.")

    return run_git_command(repo_path, ["commit", "-m", clean_message])


def _rename_origins(repo_path: str, paths: List[str]) -> List[str]:
    """Origens das renomeações cujo destino está em `paths` (para o rename entrar completo)."""
    output = run_git_command(repo_path, ["status", "--short"], strip=False)
    selected = set(paths)
    origins = []

    for line in (output or "").splitlines():
        if len(line) > 3 and " -> " in line:
            origin, destination = line[3:].strip().split(" -> ", 1)
            if destination in selected:
                origins.append(origin)

    return origins


def commit_selected_files(repo_path: str, message: str, paths: List[str]) -> str:
    """Commita apenas os `paths` informados; o restante (inclusive o já em stage) fica intacto."""
    clean_message = message.strip()

    if not clean_message:
        raise GitServiceError("A mensagem de commit não pode estar vazia.")

    if not paths:
        raise GitServiceError("Selecione ao menos um arquivo para o commit.")

    targets = list(dict.fromkeys(paths + _rename_origins(repo_path, paths)))

    # "add -A -- <paths>" cobre arquivos novos e removidos; "commit --only" ignora o resto do stage.
    # A origem de um rename já saiu do índice e do disco, então só os destinos vão no "add".
    run_git_command(repo_path, ["add", "-A", "--", *paths])
    return run_git_command(repo_path, ["commit", "--only", "-m", clean_message, "--", *targets])


def is_last_commit_pushed(repo_path: str, branch_name: str) -> bool:
    """True se o último commit já existe no upstream (amend exigirá force push)."""
    if not has_upstream(repo_path, branch_name):
        return False

    ahead = run_git_command(repo_path, ["rev-list", "--count", "@{u}..HEAD"])
    return ahead.strip() == "0"


def amend_commit(repo_path: str, message: str | None = None, paths: List[str] | None = None) -> str:
    """Inclui alterações no último commit.

    Com `paths`, só esses arquivos entram (o restante, inclusive o já em stage, fica
    intacto); lista vazia altera apenas a mensagem. Sem `paths`, inclui tudo.
    Sem mensagem, mantém a original (`--no-edit`).
    """
    clean_message = (message or "").strip()

    if paths is None:
        stage_all_changes(repo_path)
        targets: List[str] = []
        scope: List[str] = []
    else:
        if not paths and not clean_message:
            raise GitServiceError("Selecione ao menos um arquivo ou digite uma nova mensagem.")
        if paths:
            # Origem de rename já saiu do índice e do disco: só os destinos vão no "add".
            run_git_command(repo_path, ["add", "-A", "--", *paths])
        targets = list(dict.fromkeys(paths + _rename_origins(repo_path, paths)))
        scope = ["--only"]

    message_args = ["-m", clean_message] if clean_message else ["--no-edit"]
    path_args = ["--", *targets] if targets else []

    return run_git_command(repo_path, ["commit", "--amend", *scope, *message_args, *path_args])
