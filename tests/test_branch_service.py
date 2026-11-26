import pytest

from services import branch_service
from services.branch_service import (
    checkout_remote_branch,
    create_branch,
    get_current_branch,
    get_local_branches,
    get_remote_branches,
    is_detached_head,
    is_git_repository,
    split_remote_ref,
)
from services.git_runner import run_git_command


def test_is_git_repository(git_repo, tmp_path):
    assert is_git_repository(git_repo) is True
    nao_repo = tmp_path / "vazio"
    nao_repo.mkdir()
    assert is_git_repository(str(nao_repo)) is False


def test_get_current_branch(git_repo):
    assert get_current_branch(git_repo) == "main"
    assert is_detached_head(git_repo) is False


def test_get_current_branch_detached_head(git_repo):
    sha = run_git_command(git_repo, ["rev-parse", "HEAD"])
    run_git_command(git_repo, ["checkout", sha])

    assert is_detached_head(git_repo) is True

    atual = get_current_branch(git_repo)
    assert atual  # não pode ser vazio
    assert sha.startswith(atual)  # é o hash abreviado


def test_get_local_branches(git_repo):
    assert get_local_branches(git_repo) == ["main"]


def test_get_remote_branches_filtra_ponteiro_e_origin(monkeypatch):
    saida = "origin\norigin/HEAD -> origin/main\norigin/main\norigin/feature/x\n"
    monkeypatch.setattr(branch_service, "run_git_command", lambda *a, **k: saida)

    assert get_remote_branches("/repo") == ["origin/main", "origin/feature/x"]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("minha feature", "feature/minha-feature"),
        ("bugfix/login", "bugfix/login"),
        ("Hotfix/Prod", "hotfix/prod"),
        ("release/1.0", "release/1.0"),
    ],
)
def test_create_branch_normaliza_nome(monkeypatch, entrada, esperado):
    capturado = {}

    def fake(repo_path, args, *a, **k):
        capturado["args"] = args
        return ""

    monkeypatch.setattr(branch_service, "run_git_command", fake)

    create_branch("/repo", entrada)

    assert capturado["args"] == ["checkout", "-b", esperado]


def test_create_branch_nome_vazio(monkeypatch):
    monkeypatch.setattr(branch_service, "run_git_command", lambda *a, **k: "")
    with pytest.raises(ValueError):
        create_branch("/repo", "   ")


def test_get_local_and_remote_branches_equivale_as_funcoes_separadas(git_repo):
    import subprocess

    from services.branch_service import (
        create_branch,
        get_local_and_remote_branches,
        get_local_branches,
        get_remote_branches,
    )

    create_branch(git_repo, "x")
    sha = subprocess.run(
        ["git", "-C", git_repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    for ref in ("refs/remotes/origin/main", "refs/remotes/origin/feature/x"):
        subprocess.run(["git", "-C", git_repo, "update-ref", ref, sha], check=True)
    subprocess.run(
        ["git", "-C", git_repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
        check=True,
    )

    local, remote = get_local_and_remote_branches(git_repo)

    assert local == get_local_branches(git_repo)
    assert remote == get_remote_branches(git_repo) == ["origin/feature/x", "origin/main"]


def _git(repo, *args):
    import subprocess

    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True)


def test_branch_overview_traz_atual_locais_remotas_e_remotes(git_repo):
    from services.branch_service import get_branch_overview

    _git(git_repo, "branch", "feature/x")
    _git(git_repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(git_repo, "update-ref", "refs/remotes/origin/feature/x", "HEAD")
    _git(git_repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    _git(git_repo, "update-ref", "refs/remotes/upstream/main", "HEAD")

    local, remote, remotes, current = get_branch_overview(git_repo)

    assert local == ["feature/x", "main"]
    assert remote == ["origin/feature/x", "origin/main", "upstream/main"]  # sem origin/HEAD
    assert remotes == ["origin", "upstream"]  # origin/HEAD também conta como remote
    assert current == "main"


def test_branch_overview_marca_a_branch_atual_certa(git_repo):
    from services.branch_service import get_branch_overview

    _git(git_repo, "checkout", "-b", "feature/y")

    assert get_branch_overview(git_repo)[3] == "feature/y"


def test_branch_overview_head_destacado_nao_informa_atual(git_repo):
    from services.branch_service import get_branch_overview

    _git(git_repo, "checkout", "--detach")

    local, _remote, _remotes, current = get_branch_overview(git_repo)

    assert local == ["main"]
    assert current is None


def test_branch_overview_sem_remote_buscado_volta_vazio(git_repo):
    from services.branch_service import get_branch_overview

    _git(git_repo, "remote", "add", "origin", "https://github.com/o/r.git")

    # Remote só na configuração (sem refs buscados): o snapshot confirma com `git remote`.
    assert get_branch_overview(git_repo)[2] == []


@pytest.fixture
def repo_com_remoto(git_repo, tmp_path):
    """Repo clonado de um bare "origin" que tem a branch feature/x e um segundo remote "upstream"."""
    bare = str(tmp_path / "origin.git")
    run_git_command(git_repo, ["init", "--bare", bare])
    run_git_command(git_repo, ["remote", "add", "origin", bare])
    run_git_command(git_repo, ["push", "origin", "main"])
    run_git_command(git_repo, ["checkout", "-b", "feature/x"])
    run_git_command(git_repo, ["push", "origin", "feature/x"])
    run_git_command(git_repo, ["checkout", "main"])
    run_git_command(git_repo, ["branch", "-D", "feature/x"])
    run_git_command(git_repo, ["fetch", "origin"])
    return git_repo


def test_split_remote_ref_usa_remotes_configurados(repo_com_remoto):
    assert split_remote_ref(repo_com_remoto, "origin/feature/x") == ("origin", "feature/x")


def test_split_remote_ref_aceita_remote_com_barra_no_nome(repo_com_remoto, tmp_path):
    run_git_command(repo_com_remoto, ["remote", "add", "team/fork", str(tmp_path / "origin.git")])
    assert split_remote_ref(repo_com_remoto, "team/fork/y") == ("team/fork", "y")


def test_split_remote_ref_rejeita_ref_que_nao_e_remota(repo_com_remoto):
    with pytest.raises(ValueError):
        split_remote_ref(repo_com_remoto, "feature/x")


def test_checkout_remote_branch_cria_local_com_tracking(repo_com_remoto):
    assert checkout_remote_branch(repo_com_remoto, "origin/feature/x") == "feature/x"

    assert get_current_branch(repo_com_remoto) == "feature/x"
    assert is_detached_head(repo_com_remoto) is False
    upstream = run_git_command(repo_com_remoto, ["rev-parse", "--abbrev-ref", "feature/x@{upstream}"])
    assert upstream == "origin/feature/x"


def test_checkout_remote_branch_com_dois_remotes_usa_o_escolhido(repo_com_remoto, tmp_path):
    outro = str(tmp_path / "upstream.git")
    run_git_command(repo_com_remoto, ["init", "--bare", outro])
    run_git_command(repo_com_remoto, ["remote", "add", "upstream", outro])
    run_git_command(repo_com_remoto, ["push", "upstream", "origin/feature/x:refs/heads/feature/x"])
    run_git_command(repo_com_remoto, ["fetch", "upstream"])

    checkout_remote_branch(repo_com_remoto, "upstream/feature/x")

    upstream = run_git_command(repo_com_remoto, ["rev-parse", "--abbrev-ref", "feature/x@{upstream}"])
    assert upstream == "upstream/feature/x"


def test_checkout_remote_branch_com_local_existente_so_troca(repo_com_remoto):
    run_git_command(repo_com_remoto, ["branch", "feature/x", "main"])

    assert checkout_remote_branch(repo_com_remoto, "origin/feature/x") == "feature/x"

    assert get_current_branch(repo_com_remoto) == "feature/x"
    # Não mexe no tracking de uma local que já existia.
    with pytest.raises(Exception):
        run_git_command(repo_com_remoto, ["rev-parse", "--abbrev-ref", "feature/x@{upstream}"])
