"""Branches protegidas: as padrão do app mais as que cada repositório acrescenta.

As padrão (`DEFAULT_PROTECTED`) valem sempre e não podem ser removidas por configuração;
o arquivo do repositório só ACRESCENTA nomes ou padrões (ex.: `staging`, `release/*`).
O arquivo fica dentro de `.git/` (não vai para o commit nem aparece no `git status`).
"""
import fnmatch
import json
import os

DEFAULT_PROTECTED = ("main", "master", "develop", "developer")
CONFIG_FILENAME = "automation-branch.json"
_KEY = "protected_branches"

# Repositório selecionado na janela: usado quando quem pergunta não informa o repositório.
_active_repo: str | None = None
# repo -> (mtime do arquivo ou None, padrões extras): evita reler o disco a cada branch testada.
_cache: dict[str, tuple[float | None, tuple[str, ...]]] = {}


def set_active_repo(repo_path: str | None) -> None:
    global _active_repo
    _active_repo = repo_path


def _git_dir(repo_path: str) -> str | None:
    dot_git = os.path.join(repo_path, ".git")
    if os.path.isdir(dot_git):
        return dot_git
    if os.path.isfile(dot_git):  # worktree/submódulo: ".git" é um arquivo "gitdir: <caminho>"
        try:
            with open(dot_git, encoding="utf-8") as handle:
                first = handle.readline().strip()
        except OSError:
            return None
        if first.startswith("gitdir:"):
            target = first[len("gitdir:"):].strip()
            return target if os.path.isabs(target) else os.path.normpath(os.path.join(repo_path, target))
    return None


def config_path(repo_path: str) -> str | None:
    git_dir = _git_dir(repo_path)
    return os.path.join(git_dir, CONFIG_FILENAME) if git_dir else None


def _clean(patterns) -> list[str]:
    seen, result = set(), []
    for pattern in patterns or []:
        pattern = str(pattern).strip()
        if pattern and pattern.lower() not in seen:
            seen.add(pattern.lower())
            result.append(pattern)
    return result


def get_extra_patterns(repo_path: str | None) -> list[str]:
    """Padrões acrescentados pelo repositório (sem as padrão). Arquivo ausente ou inválido = nenhum."""
    if not repo_path:
        return []
    path = config_path(repo_path)
    if not path:
        return []

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        _cache[repo_path] = (None, ())
        return []

    cached = _cache.get(repo_path)
    if cached and cached[0] == mtime:
        return list(cached[1])

    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        extras = _clean(data.get(_KEY, [])) if isinstance(data, dict) else []
    except (OSError, ValueError, AttributeError):
        extras = []  # arquivo ilegível/corrompido: segue só com as padrão

    _cache[repo_path] = (mtime, tuple(extras))
    return extras


def get_protected_patterns(repo_path: str | None = None) -> list[str]:
    """Padrão + extras do repositório (o informado ou o selecionado), sem repetir."""
    repo_path = repo_path or _active_repo
    return _clean([*DEFAULT_PROTECTED, *get_extra_patterns(repo_path)])


def matches_any(branch_name: str, patterns) -> bool:
    """True se o nome (sem maiúsculas/minúsculas) bate com algum nome ou padrão com `*`."""
    name = (branch_name or "").strip().lower()
    if not name:
        return False
    return any(fnmatch.fnmatchcase(name, str(pattern).strip().lower()) for pattern in patterns if str(pattern).strip())


def is_protected(branch_name: str, repo_path: str | None = None) -> bool:
    return matches_any(branch_name, get_protected_patterns(repo_path))


def save_extra_patterns(repo_path: str, patterns) -> list[str]:
    """Grava os padrões extras do repositório e devolve a lista gravada.

    Lista vazia apaga o arquivo (volta às padrão). Levanta ValueError se não achar a pasta .git.
    """
    path = config_path(repo_path)
    if not path:
        raise ValueError("Não foi possível localizar a pasta .git deste repositório.")

    cleaned = [p for p in _clean(patterns) if p.lower() not in {d.lower() for d in DEFAULT_PROTECTED}]

    if not cleaned:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    else:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({_KEY: cleaned}, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    _cache.pop(repo_path, None)
    return cleaned
