import os
import re
from typing import List, Dict, Any

import requests

from services.branch_service import get_origin_remote_url


def _parse_github_repo(origin_url: str) -> tuple[str, str] | tuple[None, None]:
    if not origin_url:
        return None, None

    ssh_match = re.match(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>.+?)(\.git)?$", origin_url)
    if ssh_match:
        return ssh_match.group("owner"), ssh_match.group("repo")

    https_match = re.match(r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(\.git)?$", origin_url)
    if https_match:
        return https_match.group("owner"), https_match.group("repo")

    return None, None


def list_open_pull_requests(repo_path: str) -> List[Dict[str, Any]]:
    origin_url = get_origin_remote_url(repo_path)
    owner, repo = _parse_github_repo(origin_url)

    if not owner or not repo:
        return []

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    try:
        response = requests.get(
            url,
            headers=headers,
            params={"state": "open", "per_page": 50},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        prs: List[Dict[str, Any]] = []
        for pr in data:
            prs.append(
                {
                    "number": pr.get("number"),
                    "title": pr.get("title", ""),
                    "head": pr.get("head", {}).get("ref", ""),
                    "base": pr.get("base", {}).get("ref", ""),
                    "url": pr.get("html_url", ""),
                }
            )

        return prs

    except Exception:
        return []