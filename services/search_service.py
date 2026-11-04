import posixpath
import re
from typing import Any, Dict, List

from services.git_runner import run_git_command

COMMIT_MODES = ("message", "author", "code")
_FORMAT = "%h%x01%s%x01%an%x01%ad"
_HASH_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")


def _parse_commit_rows(output: str) -> List[Dict[str, Any]]:
    rows = []

    for line in (output or "").splitlines():
        parts = line.split("\x01")
        if len(parts) < 4:
            continue
        rows.append({"hash": parts[0], "subject": parts[1], "author": parts[2], "date": parts[3]})

    return rows


def search_commits(repo_path: str, query: str, mode: str = "message", limit: int = 50) -> List[Dict[str, Any]]:
    """Busca commits em todas as branches (o histórico da tela mostra só os últimos).

    mode: "message" (mensagem), "author" (autor) ou "code" (commits que adicionaram ou removeram
    o texto, `git log -S`). Um hash completo ou abreviado é sempre procurado primeiro.
    """
    query = query.strip()
    if not query:
        return []

    if mode not in COMMIT_MODES:
        raise ValueError(f"Modo de busca inválido: {mode}")

    # --fixed-strings: o que o usuário digita é texto, não expressão regular.
    base = ["log", "--all", f"-n{limit}", "--date=short", f"--pretty=format:{_FORMAT}", "--fixed-strings"]

    if mode == "message":
        filters = ["--regexp-ignore-case", f"--grep={query}"]
    elif mode == "author":
        filters = ["--regexp-ignore-case", f"--author={query}"]
    else:
        filters = ["-S", query]

    rows = _parse_commit_rows(run_git_command(repo_path, [*base, *filters], strip=False))

    if _HASH_RE.match(query):
        rows = _prepend_hash_match(repo_path, query, rows)

    return rows[:limit]


def _prepend_hash_match(repo_path: str, query: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        output = run_git_command(
            repo_path,
            ["log", "-1", "--date=short", f"--pretty=format:{_FORMAT}", f"{query}^{{commit}}"],
            strip=False,
        )
    except Exception:
        return rows  # não é um commit (ou o prefixo é ambíguo): segue só com os outros resultados

    found = _parse_commit_rows(output)
    if not found:
        return rows

    return found + [row for row in rows if row["hash"] != found[0]["hash"]]


def get_file_history(repo_path: str, path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Commits que mexeram no arquivo, seguindo renomeações."""
    output = run_git_command(
        repo_path,
        ["log", "--follow", f"-n{limit}", "--date=short", f"--pretty=format:{_FORMAT}", "--", path],
        strip=False,
    )
    return _parse_commit_rows(output)


def list_repo_files(repo_path: str) -> List[str]:
    """Arquivos rastreados e não ignorados (inclui os novos ainda não commitados)."""
    output = run_git_command(
        repo_path,
        ["-c", "core.quotepath=off", "ls-files", "--cached", "--others", "--exclude-standard"],
        strip=False,
    )
    return sorted({line for line in (output or "").splitlines() if line})


def filter_paths(paths: List[str], query: str, limit: int = 100) -> List[str]:
    """Filtra caminhos por texto (todas as palavras devem aparecer); nome do arquivo vem primeiro."""
    terms = [term for term in query.lower().split() if term]
    if not terms:
        return []

    scored = []
    for path in paths:
        lowered = path.lower()
        if not all(term in lowered for term in terms):
            continue

        name = posixpath.basename(lowered)
        in_name = all(term in name for term in terms)

        if in_name and name.startswith(terms[0]):
            rank = 0  # o nome do arquivo começa com o que foi digitado
        elif in_name:
            rank = 1  # o nome contém tudo
        else:
            rank = 2  # só o caminho inteiro contém
        scored.append((rank, len(path), path))

    scored.sort()
    return [path for _rank, _length, path in scored[:limit]]


def filter_branches(local: List[str], remote: List[str], query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Branches que contêm o texto. Remota só aparece se não houver local com o mesmo nome."""
    term = query.strip().lower()
    if not term:
        return []

    local_set = set(local)
    results = [{"name": name, "remote": False} for name in local if term in name.lower()]

    for name in remote:
        short = name.split("/", 1)[1] if "/" in name else name
        if short in local_set or term not in name.lower():
            continue
        results.append({"name": name, "remote": True})

    return results[:limit]
