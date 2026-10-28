import os
import re
import time
from typing import Callable, List, Dict, Any, Optional

import requests

from services.branch_service import get_origin_remote_url, get_current_branch
from services.git_runner import GitServiceError
from services.session_service import load_session


# Cache curto da listagem de PRs abertos. A UI chama list_open_pull_requests
# a cada sincronização de branch; sem cache isso estoura o rate limit da API
# do GitHub (60 req/h por IP quando não há token).
_PR_CACHE: Dict[tuple, tuple] = {}
_PR_CACHE_TTL = 30.0


def invalidate_pull_request_cache(repo_path: str | None = None) -> None:
    if repo_path is None:
        _PR_CACHE.clear()
        return
    try:
        key = _get_repo_info(repo_path)
    except GitServiceError:
        _PR_CACHE.clear()
        return
    _PR_CACHE.pop(key, None)


# Estados possíveis de um PR do ponto de vista de "dá para mergear?".
PR_READY = "ready"          # pode mergear agora
PR_PENDING = "pending"      # checks ainda em execução / não iniciaram
PR_FAILED = "failed"        # algum check falhou
PR_CONFLICT = "conflict"    # conflito com a branch base
PR_BEHIND = "behind"        # branch desatualizada em relação à base
PR_BLOCKED = "blocked"      # bloqueado por outra regra (review, rascunho...)
PR_CLOSED = "closed"        # já mergeado ou fechado

_STATUS_CACHE: Dict[tuple, tuple] = {}
_STATUS_CACHE_TTL = 10.0

# Guarda, por repositório, se o auto-merge do GitHub está habilitado. Ele depende de
# uma configuração de admin ("Allow auto-merge"); sem ela o app cai no fluxo local.
_AUTO_MERGE_SUPPORT: Dict[tuple, bool] = {}

_GRAPHQL_URL = "https://api.github.com/graphql"
_AUTO_MERGE_METHODS = {"merge": "MERGE", "squash": "SQUASH", "rebase": "REBASE"}

_CHECK_SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}


class AutoMergeUnavailableError(GitServiceError):
    """O auto-merge do GitHub não pode ser usado neste repositório/PR."""


class PullRequestReadyError(GitServiceError):
    """O PR já está pronto para merge, não há o que agendar."""


def invalidate_pull_request_status_cache() -> None:
    _STATUS_CACHE.clear()


def _http_error_message(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    try:
        return response.json().get("message", str(exc))
    except Exception:
        return str(exc)


_GITHUB_HOSTS = {"github.com", "www.github.com"}


def _parse_github_repo(origin_url: str) -> tuple[str | None, str | None]:
    """Extrai (owner, repo) da URL do remote origin.

    Cobre as formas usadas na prática:
      - git@github.com:owner/repo(.git)
      - https://github.com/owner/repo(.git)(/)
      - https://user:token@github.com/owner/repo.git
      - ssh://git@github.com(:22)/owner/repo.git
      - git://github.com/owner/repo.git
    """
    if not origin_url:
        return None, None

    url = origin_url.strip()

    scp_match = re.match(r"^[\w.+-]+@([\w.-]+):(.+)$", url)
    if scp_match:
        host, path = scp_match.group(1), scp_match.group(2)
    else:
        proto_match = re.match(r"^(?:ssh|git|https?)://(.+)$", url, re.IGNORECASE)
        if not proto_match:
            return None, None

        rest = proto_match.group(1).split("@", 1)[-1]  # descarta credenciais
        if "/" not in rest:
            return None, None

        host, path = rest.split("/", 1)
        host = host.split(":", 1)[0]  # descarta a porta

    if host.lower() not in _GITHUB_HOSTS:
        return None, None

    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]

    parts = path.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None

    return parts[0], parts[1]


def _get_repo_info(repo_path: str) -> tuple[str, str]:
    origin_url = get_origin_remote_url(repo_path)
    owner, repo = _parse_github_repo(origin_url)

    if not owner or not repo:
        raise GitServiceError(
            "Não foi possível identificar o repositório GitHub a partir do remote origin."
        )

    return owner, repo


def _resolve_access_token(require_token: bool = False) -> str | None:
    session = load_session()
    token = session.get("access_token") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    if require_token and not token:
        raise GitServiceError(
            "Nenhum token GitHub encontrado. Faça login pelo Profile ou configure GITHUB_TOKEN/GH_TOKEN."
        )

    return token


def _get_headers(require_token: bool = False) -> dict:
    token = _resolve_access_token(require_token=require_token)

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def list_open_pull_requests(repo_path: str, use_cache: bool = True) -> List[Dict[str, Any]]:
    owner, repo = _get_repo_info(repo_path)
    cache_key = (owner, repo)
    now = time.monotonic()

    if use_cache:
        cached = _PR_CACHE.get(cache_key)
        if cached is not None and now - cached[0] < _PR_CACHE_TTL:
            return [dict(pr) for pr in cached[1]]

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

        _PR_CACHE[cache_key] = (now, [dict(pr) for pr in prs])
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

        invalidate_pull_request_cache(repo_path)

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

        invalidate_pull_request_cache(repo_path)
        invalidate_pull_request_status_cache()

        return {
            "merged": data.get("merged", False),
            "message": data.get("message", ""),
            "sha": data.get("sha", ""),
        }

    except requests.RequestException as exc:
        message = _http_error_message(exc)
        status_code = getattr(getattr(exc, "response", None), "status_code", None)

        if status_code == 405:
            message = (
                "O GitHub ainda não permite o merge: os checks obrigatórios não foram "
                f"concluídos ou há outra regra de proteção pendente. ({message})"
            )
        elif status_code in (403, 404):
            message = (
                "Sem permissão para mergear neste repositório. Verifique se o seu token "
                f"tem acesso de escrita. ({message})"
            )

        raise GitServiceError(f"Erro ao mergear Pull Request: {message}") from exc


# ---------------------------------------------------------------------------
# Estado de mergeabilidade (checks + regras de proteção)
# ---------------------------------------------------------------------------

def _classify_checks(check_runs: List[Dict[str, Any]], commit_statuses: List[Dict[str, Any]]) -> str:
    """Resume check-runs (GitHub Actions) e commit statuses (integrações) em um estado.

    Retorna "failed", "pending", "success" ou "none" (nenhum check registrado ainda).
    """
    states: List[str] = []

    for run in check_runs:
        if run.get("status") != "completed":
            states.append("pending")
        elif run.get("conclusion") in _CHECK_SUCCESS_CONCLUSIONS:
            states.append("success")
        else:
            states.append("failed")

    for item in commit_statuses:
        state = item.get("state")
        if state == "success":
            states.append("success")
        elif state == "pending":
            states.append("pending")
        else:
            states.append("failed")

    if not states:
        return "none"
    if "failed" in states:
        return "failed"
    if "pending" in states:
        return "pending"
    return "success"


def _status(state: str, label: str, detail: str = "", auto_merge: bool = False) -> Dict[str, Any]:
    return {"state": state, "label": label, "detail": detail, "auto_merge": auto_merge}


def _derive_status(pull: Dict[str, Any], load_checks: Callable[[], str]) -> Dict[str, Any]:
    """Converte o JSON de GET /pulls/{n} no estado de merge.

    `mergeable_state` já considera todas as regras do branch protection (checks,
    reviews, branch atualizada). Os checks só são consultados quando ele diz "blocked"
    ou ainda não foi calculado, para separar "em execução" de "falhou".
    """
    auto_merge = bool(pull.get("auto_merge"))

    if pull.get("merged") or pull.get("state") == "closed":
        return _status(PR_CLOSED, "PR fechado", auto_merge=auto_merge)

    if pull.get("draft"):
        return _status(
            PR_BLOCKED, "Rascunho", "O PR está como rascunho. Marque como pronto para revisão.", auto_merge
        )

    mergeable_state = pull.get("mergeable_state")

    if mergeable_state in ("clean", "has_hooks"):
        return _status(PR_READY, "Pronto para merge", auto_merge=auto_merge)

    if mergeable_state == "unstable":
        return _status(
            PR_READY,
            "Pronto para merge",
            "Há checks não obrigatórios falhando, mas o merge é permitido.",
            auto_merge,
        )

    if mergeable_state == "dirty":
        return _status(
            PR_CONFLICT, "Conflito com a base", "Resolva os conflitos antes de mergear.", auto_merge
        )

    if mergeable_state == "behind":
        return _status(
            PR_BEHIND,
            "Branch desatualizada",
            "A base recebeu novos commits. Atualize a branch do PR.",
            auto_merge,
        )

    # "blocked", "unknown" ou ainda não calculado (null logo após o push).
    checks = load_checks()

    if checks == "failed":
        return _status(PR_FAILED, "Checks falharam", "Algum check do PR falhou.", auto_merge)

    if checks == "success" and mergeable_state == "blocked":
        return _status(
            PR_BLOCKED,
            "Bloqueado por regra",
            "Checks ok, mas o GitHub exige algo mais (ex.: aprovação de review).",
            auto_merge,
        )

    return _status(
        PR_PENDING, "Aguardando checks", "Os checks ainda estão em execução ou não iniciaram.", auto_merge
    )


def get_pull_request_merge_status(
    repo_path: str, pr_number: int, use_cache: bool = True
) -> Dict[str, Any]:
    """Informa se um PR pode ser mergeado agora, sem exigir nenhuma configuração do repositório.

    Só usa endpoints de leitura. Retorna {"state", "label", "detail", "auto_merge"}.
    """
    owner, repo = _get_repo_info(repo_path)
    cache_key = (owner, repo, pr_number)
    now = time.monotonic()

    if use_cache:
        cached = _STATUS_CACHE.get(cache_key)
        if cached is not None and now - cached[0] < _STATUS_CACHE_TTL:
            return dict(cached[1])

    headers = _get_headers(require_token=False)
    base_url = f"https://api.github.com/repos/{owner}/{repo}"

    def load_checks() -> str:
        sha = pull.get("head", {}).get("sha", "")
        if not sha:
            return "none"

        runs = requests.get(
            f"{base_url}/commits/{sha}/check-runs",
            headers=headers,
            params={"per_page": 100},
            timeout=10,
        )
        runs.raise_for_status()

        statuses = requests.get(
            f"{base_url}/commits/{sha}/status",
            headers=headers,
            params={"per_page": 100},
            timeout=10,
        )
        statuses.raise_for_status()

        return _classify_checks(
            runs.json().get("check_runs", []),
            statuses.json().get("statuses", []),
        )

    try:
        response = requests.get(f"{base_url}/pulls/{pr_number}", headers=headers, timeout=10)
        response.raise_for_status()
        pull = response.json()

        result = _derive_status(pull, load_checks)

    except requests.RequestException as exc:
        raise GitServiceError(
            f"Erro ao consultar o status do Pull Request: {_http_error_message(exc)}"
        ) from exc

    _STATUS_CACHE[cache_key] = (now, dict(result))
    return result


# ---------------------------------------------------------------------------
# Auto-merge do GitHub (opcional: exige "Allow auto-merge" ligado por um admin)
# ---------------------------------------------------------------------------

def is_auto_merge_supported(repo_path: str) -> bool | None:
    """True/False se já sabemos o suporte do repositório; None se ainda não foi tentado."""
    try:
        return _AUTO_MERGE_SUPPORT.get(_get_repo_info(repo_path))
    except GitServiceError:
        return None


def enable_auto_merge(repo_path: str, pr_number: int, merge_method: str = "merge") -> None:
    """Pede ao GitHub para mergear o PR assim que os checks obrigatórios passarem.

    Levanta AutoMergeUnavailableError quando o recurso não está disponível (repositório
    sem "Allow auto-merge", sem branch protection ou token sem permissão) e
    PullRequestReadyError quando o PR já pode ser mergeado direto.
    """
    owner, repo = _get_repo_info(repo_path)
    cache_key = (owner, repo)

    if _AUTO_MERGE_SUPPORT.get(cache_key) is False:
        raise AutoMergeUnavailableError("Auto-merge não está habilitado neste repositório.")

    headers = _get_headers(require_token=True)
    method = _AUTO_MERGE_METHODS.get(merge_method, "MERGE")

    try:
        pull_response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=headers,
            timeout=10,
        )
        pull_response.raise_for_status()
        node_id = pull_response.json().get("node_id", "")

        response = requests.post(
            _GRAPHQL_URL,
            headers=headers,
            json={
                "query": (
                    "mutation($id: ID!, $method: PullRequestMergeMethod!) {"
                    " enablePullRequestAutoMerge(input: {pullRequestId: $id, mergeMethod: $method}) {"
                    " pullRequest { number } } }"
                ),
                "variables": {"id": node_id, "method": method},
            },
            timeout=10,
        )
        response.raise_for_status()
        errors = response.json().get("errors") or []

    except requests.RequestException as exc:
        raise GitServiceError(f"Erro ao ativar auto-merge: {_http_error_message(exc)}") from exc

    if not errors:
        _AUTO_MERGE_SUPPORT[cache_key] = True
        invalidate_pull_request_status_cache()
        return

    message = "; ".join(str(err.get("message", "")) for err in errors)
    lowered = message.lower()

    if "auto merge is not allowed" in lowered:
        # Configuração do repositório: vale para todos os PRs, então guarda em cache.
        _AUTO_MERGE_SUPPORT[cache_key] = False
        raise AutoMergeUnavailableError(message)

    if "clean status" in lowered:
        raise PullRequestReadyError(message)

    if "protected branch rules not configured" in lowered or "resource not accessible" in lowered:
        # Específico da branch base ou do token: não afeta os demais PRs.
        raise AutoMergeUnavailableError(message)

    raise GitServiceError(f"Erro ao ativar auto-merge: {message}")


def update_pull_request_branch(repo_path: str, pr_number: int) -> str:
    """Atualiza a branch do PR com a base (equivale ao botão "Update branch" do GitHub)."""
    owner, repo = _get_repo_info(repo_path)
    headers = _get_headers(require_token=True)

    try:
        response = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/update-branch",
            headers=headers,
            json={},
            timeout=10,
        )
        response.raise_for_status()
        message = response.json().get("message", "")

    except requests.RequestException as exc:
        raise GitServiceError(
            f"Erro ao atualizar a branch do Pull Request: {_http_error_message(exc)}"
        ) from exc

    invalidate_pull_request_status_cache()
    return message
