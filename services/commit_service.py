import os
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


# quotepath=off evita que acentos virem escapes octais (ex.: "a\303\247.txt").
_STATUS_ARGS = ["-c", "core.quotepath=off", "status", "--short"]
MAX_DIFF_CHARS = 200_000


def _parse_status_path(raw: str) -> str:
    # Formato do "git status --short": "XY <caminho>" (caminho a partir da coluna 3).
    # Em renomeações vem "R  origem -> destino"; mostramos o destino.
    file_path = raw[3:].strip() if len(raw) > 3 else raw.strip()
    if " -> " in file_path:
        file_path = file_path.split(" -> ", 1)[1]
    # Caminhos com espaço vêm entre aspas no "status --short".
    if len(file_path) >= 2 and file_path[0] == file_path[-1] == '"':
        file_path = file_path[1:-1]
    return file_path


def get_changed_files(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, _STATUS_ARGS, strip=False)

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
    output = run_git_command(repo_path, _STATUS_ARGS, strip=False)

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
    output = run_git_command(repo_path, _STATUS_ARGS, strip=False)
    selected = set(paths)
    origins = []

    for line in (output or "").splitlines():
        if len(line) > 3 and " -> " in line:
            origin, destination = line[3:].strip().split(" -> ", 1)
            if destination.strip('"') in selected:
                origins.append(origin.strip('"'))

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


def get_file_diff(repo_path: str, path: str, staged: bool, untracked: bool = False) -> str:
    """Diff de um arquivo: do stage (`staged`), do working tree ou, se novo, o conteúdo inteiro."""
    if untracked:
        full_path = os.path.join(repo_path, path)
        if os.path.isdir(full_path):
            return "(pasta não rastreada)"
        try:
            with open(full_path, "rb") as handle:
                raw = handle.read(MAX_DIFF_CHARS + 1)
        except OSError as exc:
            raise GitServiceError(f"Não foi possível ler {path}: {exc}") from exc
        if b"\0" in raw:
            return "(arquivo binário)"
        text = raw[:MAX_DIFF_CHARS].decode("utf-8", errors="replace")
        body = "".join(f"+{line}" for line in text.splitlines(keepends=True))
        header = f"--- /dev/null\n+++ b/{path}\n"
        diff = header + body
    else:
        args = ["diff", "--cached"] if staged else ["diff"]
        diff = run_git_command(repo_path, [*args, "--", path], strip=False)

    if not diff.strip():
        return "(sem diferenças)"

    if len(diff) > MAX_DIFF_CHARS:
        return diff[:MAX_DIFF_CHARS] + "\n\n... diff truncado ..."

    return diff


def stage_files(repo_path: str, paths: List[str]) -> str:
    if not paths:
        raise GitServiceError("Nenhum arquivo informado.")
    return run_git_command(repo_path, ["add", "-A", "--", *paths])


def unstage_files(repo_path: str, paths: List[str]) -> str:
    """Tira do stage sem tocar no working tree (renomeações saem completas)."""
    if not paths:
        raise GitServiceError("Nenhum arquivo informado.")

    targets = list(dict.fromkeys(paths + _rename_origins(repo_path, paths)))

    try:
        return run_git_command(repo_path, ["restore", "--staged", "--", *targets])
    except GitServiceError:
        # Repositório sem nenhum commit: não há HEAD para restaurar.
        return run_git_command(repo_path, ["rm", "-r", "--cached", "-q", "--", *targets])


def discard_changes(repo_path: str, paths: List[str]) -> str:
    """Descarta alterações NÃO commitadas do working tree (irreversível).

    Arquivos rastreados voltam ao conteúdo do stage; não rastreados são apagados.
    """
    if not paths:
        raise GitServiceError("Nenhum arquivo informado.")

    output = run_git_command(repo_path, _STATUS_ARGS, strip=False)
    untracked = {
        _parse_status_path(line)
        for line in (output or "").splitlines()
        if line.startswith("??")
    }

    tracked_paths = [p for p in paths if p not in untracked]
    untracked_paths = [p for p in paths if p in untracked]

    if tracked_paths:
        run_git_command(repo_path, ["restore", "--", *tracked_paths])
    if untracked_paths:
        run_git_command(repo_path, ["clean", "-f", "-d", "--", *untracked_paths])

    return ""


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
