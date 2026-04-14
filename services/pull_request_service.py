import os
import re
from typing import List, Dict, Any, Optional

import requests

from services.branch_service import get_origin_remote_url, get_current_branch
from services.git_runner import GitServiceError


def _parse_github_repo(origin_url: str) -> tuple[str | None, str | None]:
    if not origin_url:
        return None, None

    ssh_match = re.match(
        r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>.+?)(\.git)?$",
        origin_url
    )
    if ssh_match:
        return ssh_match.group("owner"), ssh_match.group("repo")

    https_match = re.match(
        r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(\.git)?$",
        origin_url
    )
    if https_match:
        return https_match.group("owner"), https_match.group("repo")

    return None, None


def _get_repo_info(repo_path: str) -> tuple[str, str]:
    origin_url = get_origin_remote_url(repo_path)
    owner, repo = _parse_github_repo(origin_url)

    if not owner or not repo:
        raise GitServiceError(
            "Não foi possível identificar o repositório GitHub a partir do remote origin."
        )

    return owner, repo


def _get_headers(require_token: bool = False) -> dict:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    if require_token and not token:
        raise GitServiceError(
            "GITHUB_TOKEN/GH_TOKEN não configurado. Defina um token para criar ou mergear Pull Requests."
        )

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def list_open_pull_requests(repo_path: str) -> List[Dict[str, Any]]:
    owner, repo = _get_repo_info(repo_path)
    headers = _get_headers(require_token=False)

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

    except requests.RequestException as exc:
        raise GitServiceError(f"Erro ao listar Pull Requests: {str(exc)}") from exc


def find_open_pull_request_by_head(repo_path: str, head_branch: str) -> Optional[Dict[str, Any]]:
    prs = list_open_pull_requests(repo_path)

    for pr in prs:
        if pr.get("head") == head_branch:
            return pr

    return None


def create_pull_request(
    repo_path: str,
    title: str,
    body: str = "",
    base_branch: str = "main",
    head_branch: str | None = None
) -> Dict[str, Any]:
    owner, repo = _get_repo_info(repo_path)
    headers = _get_headers(require_token=True)

    if not head_branch:
        head_branch = get_current_branch(repo_path)

    if not title.strip():
        raise GitServiceError("O título do Pull Request não pode ficar vazio.")

    existing_pr = find_open_pull_request_by_head(repo_path, head_branch)
    if existing_pr:
        return existing_pr

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    payload = {
        "title": title.strip(),
        "body": body.strip(),
        "head": head_branch,
        "base": base_branch,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        pr = response.json()

        return {
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "head": pr.get("head", {}).get("ref", ""),
            "base": pr.get("base", {}).get("ref", ""),
            "url": pr.get("html_url", ""),
        }

    except requests.RequestException as exc:
        try:
            details = exc.response.json()
            message = details.get("message", str(exc))
        except Exception:
            message = str(exc)

        raise GitServiceError(f"Erro ao criar Pull Request: {message}") from exc


def merge_pull_request(
    repo_path: str,
    pr_number: int,
    commit_title: str | None = None,
    merge_method: str = "merge"
) -> Dict[str, Any]:
    owner, repo = _get_repo_info(repo_path)
    headers = _get_headers(require_token=True)

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/merge"
    payload: Dict[str, Any] = {
        "merge_method": merge_method
    }

    if commit_title:
        payload["commit_title"] = commit_title.strip()

    try:
        response = requests.put(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        return {
            "merged": data.get("merged", False),
            "message": data.get("message", ""),
            "sha": data.get("sha", ""),
        }

    except requests.RequestException as exc:
        try:
            details = exc.response.json()
            message = details.get("message", str(exc))
        except Exception:
            message = str(exc)

        raise GitServiceError(f"Erro ao mergear Pull Request: {message}") from exc