import re
from typing import List, Dict, Any

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