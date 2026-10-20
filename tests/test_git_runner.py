import subprocess

import pytest

from services import git_runner
from services.git_runner import GitServiceError, run_git_command


def test_run_git_command_retorna_saida(git_repo):
    saida = run_git_command(git_repo, ["rev-parse", "--is-inside-work-tree"])
    assert saida == "true"


def test_run_git_command_erro_vira_git_service_error(git_repo):
    with pytest.raises(GitServiceError):
        run_git_command(git_repo, ["checkout", "branch-que-nao-existe"])


def test_run_git_command_strip_false_preserva_espacos_a_esquerda(monkeypatch):
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="  M arquivo.py\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    assert run_git_command("/x", ["status"], strip=False) == "  M arquivo.py"
    assert run_git_command("/x", ["status"], strip=True) == "M arquivo.py"


def test_run_git_command_timeout(monkeypatch):
    def estoura(*a, **k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(subprocess, "run", estoura)

    with pytest.raises(GitServiceError, match="tempo limite"):
        run_git_command("/x", ["pull"], timeout=1)


def test_run_git_command_git_ausente(monkeypatch):
    def sem_git(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", sem_git)

    with pytest.raises(GitServiceError, match="Git não encontrado"):
        run_git_command("/x", ["status"])


def test_network_timeout_maior_que_o_padrao():
    assert git_runner.NETWORK_TIMEOUT > git_runner.DEFAULT_TIMEOUT
