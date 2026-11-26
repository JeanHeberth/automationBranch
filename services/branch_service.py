from typing import List

from services.git_runner import run_git_command, GitServiceError


def is_git_repository(repo_path: str) -> bool:
    try:
        output = run_git_command(repo_path, ["rev-parse", "--is-inside-work-tree"])
        return output.strip() == "true"
    except GitServiceError:
        return False


def get_local_branches(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["branch", "--format=%(refname:short)"])
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_remote_branches(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["branch", "-r", "--format=%(refname:short)"])
    if not output:
        return []

    branches = []
    for line in output.splitlines():
        branch = line.strip()
        # Ignora linhas vazias, o ponteiro simbólico (ex.: "origin/HEAD -> origin/main")
        # e o próprio "origin" que o %(refname:short) gera para refs/remotes/origin/HEAD.
        if not branch or "->" in branch or "/" not in branch:
            continue
        branches.append(branch)

    return branches


def _parse_track(track: str) -> tuple[int, int]:
    """Lê o `%(upstream:track,nobracket)` ("ahead 2, behind 1", "gone", "") como (ahead, behind)."""
    ahead = behind = 0
    for part in track.split(","):
        words = part.split()
        if len(words) == 2 and words[1].isdigit():
            if words[0] == "ahead":
                ahead = int(words[1])
            elif words[0] == "behind":
                behind = int(words[1])
    return ahead, behind


def get_branch_overview(repo_path: str) -> tuple[List[str], List[str], List[str], str | None]:
    """Locais, remotas, nomes dos remotes e branch atual, tudo num único processo git.

    Cada processo git custa caro no Windows; o `for-each-ref` já traz o que
    `get_local_and_remote_branches`, `get_remotes` e `get_current_branch` buscariam
    em três processos à parte. Retorna (locais, remotas, remotes, atual):
      - `atual` é None em HEAD destacado ou repositório sem commits (use `get_current_branch`);
      - `remotes` vem dos refs buscados, então fica vazio se nenhum remote foi buscado ainda
        (use `get_remotes` nesse caso).
    """
    local, remote, remotes, current, _tracking = get_branch_overview_with_tracking(repo_path)
    return local, remote, remotes, current


def get_branch_overview_with_tracking(
    repo_path: str,
) -> tuple[List[str], List[str], List[str], str | None, dict[str, tuple[int, int]]]:
    """Como `get_branch_overview`, mais o quanto cada local está à frente/atrás do upstream.

    O 5º item mapeia branch local -> (ahead, behind) só para quem difere do upstream; branch
    sem upstream (ou em dia) não aparece. Vem do mesmo `for-each-ref`, sem processo extra. O
    número é relativo ao que foi buscado por último: sem fetch ele pode estar defasado.
    """
    # strip=False: a primeira linha começa com o marcador de %(HEAD) (" " ou "*"), que não pode ser cortado.
    output = run_git_command(
        repo_path,
        ["for-each-ref", "--format=%(HEAD)%(refname)%09%(upstream:track,nobracket)", "refs/heads", "refs/remotes"],
        strip=False,
    )

    tracking: dict[str, tuple[int, int]] = {}
    local: List[str] = []
    remote: List[str] = []
    remotes: set[str] = set()
    current: str | None = None

    for line in output.splitlines():
        if not line.strip():
            continue

        is_head = line.startswith("*")
        ref, _sep, track = line[1:].partition("\t")
        ref = ref.strip()

        if ref.startswith("refs/heads/"):
            name = ref[len("refs/heads/"):]
            local.append(name)
            if is_head:
                current = name
            ahead_behind = _parse_track(track)
            if ahead_behind != (0, 0):
                tracking[name] = ahead_behind
        elif ref.startswith("refs/remotes/"):
            name = ref[len("refs/remotes/"):]
            if "/" in name:
                remotes.add(name.split("/", 1)[0])
            # Ignora o ponteiro simbólico origin/HEAD (mesmo critério de get_remote_branches).
            if "/" not in name or name.endswith("/HEAD"):
                continue
            remote.append(name)

    return local, remote, sorted(remotes), current, tracking


def get_local_and_remote_branches(repo_path: str) -> tuple[List[str], List[str]]:
    """Local e remotas num único processo git (equivale a get_local_branches + get_remote_branches)."""
    local, remote, _remotes, _current = get_branch_overview(repo_path)
    return local, remote


def get_remotes(repo_path: str) -> List[str]:
    output = run_git_command(repo_path, ["remote"])
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_origin_remote_url(repo_path: str) -> str:
    try:
        return run_git_command(repo_path, ["remote", "get-url", "origin"]).strip()
    except GitServiceError:
        return ""


def is_detached_head(repo_path: str) -> bool:
    try:
        run_git_command(repo_path, ["symbolic-ref", "-q", "HEAD"])
        return False
    except GitServiceError:
        return True


def get_current_branch(repo_path: str) -> str:
    output = run_git_command(repo_path, ["branch", "--show-current"]).strip()
    if output:
        return output

    # Detached HEAD (ou repositório sem commits): "--show-current" volta vazio.
    # Usa o hash abreviado, que continua sendo uma revisão válida para "git log".
    try:
        return run_git_command(repo_path, ["rev-parse", "--short", "HEAD"]).strip()
    except GitServiceError:
        return ""


def checkout_branch(repo_path: str, branch_name: str) -> str:
    return run_git_command(repo_path, ["checkout", branch_name])


def split_remote_ref(repo_path: str, remote_ref: str) -> tuple[str, str]:
    """Separa "origin/feature/x" em ("origin", "feature/x").

    Confere contra os remotes configurados (o nome do remote também pode ter "/"),
    preferindo o mais longo; é o que evita adivinhar com `split("/", 1)`.
    """
    for remote in sorted(get_remotes(repo_path), key=len, reverse=True):
        prefix = f"{remote}/"
        if remote_ref.startswith(prefix) and len(remote_ref) > len(prefix):
            return remote, remote_ref[len(prefix):]
    raise ValueError(f"'{remote_ref}' não é uma branch remota de nenhum remote configurado.")


def local_branch_exists(repo_path: str, branch_name: str) -> bool:
    try:
        run_git_command(repo_path, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
        return True
    except GitServiceError:
        return False


def checkout_remote_branch(repo_path: str, remote_ref: str) -> str:
    """Faz checkout de uma branch remota ("origin/feature/x") e devolve o nome da branch local.

    Se já existe uma local com esse nome, só troca para ela (sem mexer no tracking).
    Caso contrário cria `feature/x` rastreando exatamente `remote_ref`, o que também
    resolve a ambiguidade de a mesma branch existir em mais de um remote e evita HEAD destacado.
    """
    _remote, local_name = split_remote_ref(repo_path, remote_ref)

    if local_branch_exists(repo_path, local_name):
        run_git_command(repo_path, ["checkout", local_name])
    else:
        run_git_command(repo_path, ["checkout", "--track", "-b", local_name, remote_ref])

    return local_name


def create_branch(repo_path: str, branch_name: str) -> str:
    branch_name = branch_name.strip()

    if not branch_name:
        raise ValueError("Nome da branch não pode ser vazio.")

    branch_name = branch_name.lower().replace(" ", "-")

    valid_prefixes = ("feature/", "bugfix/", "hotfix/", "release/")

    if not branch_name.startswith(valid_prefixes):
        branch_name = f"feature/{branch_name}"

    return run_git_command(repo_path, ["checkout", "-b", branch_name])


def has_upstream(repo_path: str, branch_name: str) -> bool:
    try:
        output = run_git_command(
            repo_path,
            ["rev-parse", "--abbrev-ref", f"{branch_name}@{{upstream}}"]
        )
        return bool(output.strip())
    except GitServiceError:
        return False

