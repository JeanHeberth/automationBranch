from typing import List, Dict

from services.git_runner import run_git_command, GitServiceError


def get_recent_commits(repo_path: str, branch_name: str, limit: int = 15) -> List[str]:
    format_string = "%h|%s|%an"
    output = run_git_command(
        repo_path,
        ["log", branch_name, f"-n{limit}", f"--pretty=format:{format_string}"]
    )

    if not output:
        return []

    commits = []
    for line in output.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commit_hash, subject, author = parts
            commits.append(f"{commit_hash.strip()} | {subject.strip()} | {author.strip()}")
        else:
            commits.append(line.strip())

    return commits


def get_changed_files(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["status", "--short"])

    if not output:
        return []

    files = []
    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue

        status = line[:2]
        file_path = line[3:].strip() if len(line) > 3 else line.strip()
        files.append(f"{status} | {file_path}")

    return files


def get_changed_files_grouped(repo_path: str) -> Dict[str, List[str]]:
    output = run_git_command(repo_path, ["status", "--short"])

    grouped = {
        "staged": [],
        "unstaged": [],
    }

    if not output:
        return grouped

    for line in output.splitlines():
        raw = line.rstrip()
        if not raw:
            continue

        index_status = raw[0]
        worktree_status = raw[1]
        file_path = raw[3:].strip() if len(raw) > 3 else raw.strip()

        if index_status != " ":
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