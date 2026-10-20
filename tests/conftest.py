import os
import subprocess

import pytest


def _run(repo: str, *args: str) -> None:
    subprocess.run(
        ["git", "-C", repo, *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path):
    """Cria um repositório Git real e isolado, com um commit inicial na branch main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    repo_str = str(repo)

    # Isola de qualquer configuração global/hooks do ambiente que roda os testes.
    os.environ.setdefault("GIT_CONFIG_NOSYSTEM", "1")

    _run(repo_str, "init")
    _run(repo_str, "checkout", "-b", "main")
    _run(repo_str, "config", "user.email", "test@example.com")
    _run(repo_str, "config", "user.name", "Test User")
    _run(repo_str, "config", "commit.gpgsign", "false")

    (repo / "README.md").write_text("# repositório de teste\n", encoding="utf-8")
    _run(repo_str, "add", "-A")
    _run(repo_str, "commit", "-m", "primeiro commit")

    return repo_str
