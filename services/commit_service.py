from typing import List

from services.git_runner import run_git_command


def get_recent_commits(repo_path: str, branch_name: str, limit: int = 15) -> List[str]:
    format_string = "%h | %s | %an"
    output = run_git_command(
        repo_path,
        ["log", branch_name, f"-n{limit}", f"--pretty=format:{format_string}"]
    )

    if not output:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]