from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List

from services.branch_service import (
    get_current_branch,
    get_local_and_remote_branches,
    get_remotes,
)
from services.commit_service import get_changed_files_grouped, get_recent_commit_rows
from services.git_runner import GitServiceError


@dataclass
class RepoSnapshot:
    branch: str
    local_branches: List[str]
    remote_branches: List[str]
    remotes: List[str]
    commit_rows: List[Dict[str, Any]] = field(default_factory=list)
    commit_error: str | None = None
    changed_files: Dict[str, List[str]] = field(default_factory=lambda: {"staged": [], "unstaged": []})
    changed_files_error: str | None = None


def collect_repo_snapshot(
    repo_path: str,
    branch_name: str | None = None,
    commit_limit: int = 25,
) -> RepoSnapshot:
    """Coleta tudo o que a UI precisa para redesenhar, com os comandos git em paralelo.

    Cada comando é um processo à parte (caro no Windows); rodando juntos o tempo total
    passa a ser o do mais lento. Pode ser chamada fora da thread da UI.
    Erros de branches/remotes propagam; erros de commits/arquivos viram texto no snapshot.
    """
    with ThreadPoolExecutor(max_workers=4) as pool:
        branch_future = pool.submit(get_current_branch, repo_path) if branch_name is None else None
        branches_future = pool.submit(get_local_and_remote_branches, repo_path)
        remotes_future = pool.submit(get_remotes, repo_path)
        files_future = pool.submit(get_changed_files_grouped, repo_path)

        if branch_future is not None:
            branch_name = branch_future.result()

        commits_future = pool.submit(get_recent_commit_rows, repo_path, branch_name, commit_limit)

        local, remote = branches_future.result()
        remotes = remotes_future.result()

        snapshot = RepoSnapshot(
            branch=branch_name,
            local_branches=local,
            remote_branches=remote,
            remotes=remotes,
        )

        try:
            snapshot.commit_rows = commits_future.result()
        except GitServiceError as exc:
            snapshot.commit_error = str(exc)

        try:
            snapshot.changed_files = files_future.result()
        except GitServiceError as exc:
            snapshot.changed_files_error = str(exc)

    return snapshot
