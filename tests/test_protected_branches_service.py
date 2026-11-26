import json
import os

import pytest

from services import protected_branches_service as pb
from services.branch_delete_service import delete_local_branch, get_deletable_local_branches, is_protected
from services.git_runner import GitServiceError, run_git_command


@pytest.fixture(autouse=True)
def _sem_repo_ativo():
    pb.set_active_repo(None)
    pb._cache.clear()
    yield
    pb.set_active_repo(None)
    pb._cache.clear()


def test_padrao_continua_protegido_sem_configuracao(git_repo):
    for nome in ("main", "master", "develop", "developer", "MAIN", " Develop "):
        assert is_protected(nome, git_repo) is True
    assert is_protected("feature/x", git_repo) is False
    assert is_protected("", git_repo) is False


def test_salvar_acrescenta_nome_e_glob(git_repo):
    saved = pb.save_extra_patterns(git_repo, ["staging", "release/*", "  ", "STAGING"])

    assert saved == ["staging", "release/*"]  # sem vazios nem repetidos (ignora maiúsculas)
    assert is_protected("staging", git_repo)
    assert is_protected("release/1.0", git_repo)
    assert is_protected("Release/2.0", git_repo)
    assert not is_protected("feature/release", git_repo)
    assert is_protected("main", git_repo)  # as padrão seguem valendo


def test_extras_nao_removem_as_padrao(git_repo):
    # Colocar "main" na lista não duplica nem tira nada; e não é gravado como extra.
    assert pb.save_extra_patterns(git_repo, ["main", "staging"]) == ["staging"]
    assert pb.get_protected_patterns(git_repo) == ["main", "master", "develop", "developer", "staging"]


def test_arquivo_fica_dentro_do_dot_git_e_nao_suja_o_status(git_repo):
    pb.save_extra_patterns(git_repo, ["staging"])

    caminho = pb.config_path(git_repo)
    assert caminho == os.path.join(git_repo, ".git", "automation-branch.json")
    assert json.load(open(caminho, encoding="utf-8")) == {"protected_branches": ["staging"]}
    assert run_git_command(git_repo, ["status", "--porcelain"]) == ""


def test_lista_vazia_apaga_o_arquivo_e_volta_ao_padrao(git_repo):
    pb.save_extra_patterns(git_repo, ["staging"])
    assert is_protected("staging", git_repo)

    assert pb.save_extra_patterns(git_repo, []) == []

    assert not os.path.exists(pb.config_path(git_repo))
    assert not is_protected("staging", git_repo)
    pb.save_extra_patterns(git_repo, [])  # apagar de novo não pode falhar


def test_arquivo_corrompido_cai_nas_padrao(git_repo):
    with open(pb.config_path(git_repo), "w", encoding="utf-8") as handle:
        handle.write("{ isto não é json")

    assert pb.get_protected_patterns(git_repo) == list(pb.DEFAULT_PROTECTED)
    assert is_protected("main", git_repo)


def test_edicao_do_arquivo_a_mao_e_relida(git_repo):
    pb.save_extra_patterns(git_repo, ["staging"])
    assert is_protected("staging", git_repo)

    caminho = pb.config_path(git_repo)
    with open(caminho, "w", encoding="utf-8") as handle:
        json.dump({"protected_branches": ["qa"]}, handle)
    os.utime(caminho, (os.path.getmtime(caminho) + 5, os.path.getmtime(caminho) + 5))

    assert is_protected("qa", git_repo)
    assert not is_protected("staging", git_repo)


def test_repositorio_ativo_vale_quando_nao_se_informa_o_repo(git_repo):
    pb.save_extra_patterns(git_repo, ["staging"])

    assert is_protected("staging") is False  # sem repo ativo
    pb.set_active_repo(git_repo)
    assert is_protected("staging") is True


def test_config_de_um_repo_nao_vaza_para_outro(git_repo, tmp_path):
    outro = tmp_path / "outro"
    outro.mkdir()
    run_git_command(str(outro), ["init"])

    pb.save_extra_patterns(git_repo, ["staging"])

    assert is_protected("staging", git_repo)
    assert not is_protected("staging", str(outro))


def test_salvar_fora_de_repositorio_levanta_erro(tmp_path):
    with pytest.raises(ValueError):
        pb.save_extra_patterns(str(tmp_path), ["staging"])


def test_git_dir_de_worktree_le_o_arquivo_gitdir(tmp_path):
    real = tmp_path / "gitdir-real"
    real.mkdir()
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")

    assert pb.config_path(str(wt)) == os.path.join(str(real), "automation-branch.json")


def test_delete_e_listagem_respeitam_a_config_do_repo(git_repo):
    run_git_command(git_repo, ["branch", "staging"])
    run_git_command(git_repo, ["branch", "release/1.0"])
    run_git_command(git_repo, ["branch", "feature/x"])
    pb.save_extra_patterns(git_repo, ["staging", "release/*"])

    assert get_deletable_local_branches(git_repo) == ["feature/x"]
    with pytest.raises(GitServiceError, match="protegida"):
        delete_local_branch(git_repo, "release/1.0")
