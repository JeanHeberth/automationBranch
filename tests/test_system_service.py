import pytest

from services import system_service as ss
from services.git_runner import GitServiceError


@pytest.fixture
def spawned(monkeypatch):
    calls = []

    def fake_popen(command, cwd=None, **kwargs):
        calls.append((command, cwd))

    monkeypatch.setattr(ss.subprocess, "Popen", fake_popen)
    return calls


@pytest.fixture
def pasta(tmp_path):
    return str(tmp_path)


def test_open_terminal_por_sistema(monkeypatch, spawned, pasta):
    monkeypatch.setattr(ss.sys, "platform", "darwin")
    ss.open_terminal(pasta)
    monkeypatch.setattr(ss.sys, "platform", "win32")
    ss.open_terminal(pasta)

    assert spawned[0] == (["open", "-a", "Terminal", pasta], None)
    assert spawned[1] == (["cmd.exe", "/c", "start", "cmd.exe"], pasta)


def test_open_terminal_linux_usa_o_primeiro_disponivel(monkeypatch, spawned, pasta):
    monkeypatch.setattr(ss.sys, "platform", "linux")
    monkeypatch.setattr(ss.shutil, "which", lambda nome: f"/usr/bin/{nome}" if nome == "konsole" else None)

    ss.open_terminal(pasta)

    assert spawned == [(["konsole"], pasta)]


def test_open_terminal_linux_sem_terminal(monkeypatch, spawned, pasta):
    monkeypatch.setattr(ss.sys, "platform", "linux")
    monkeypatch.setattr(ss.shutil, "which", lambda nome: None)

    with pytest.raises(GitServiceError, match="Nenhum terminal"):
        ss.open_terminal(pasta)


def test_open_editor_prefere_variavel_de_ambiente(monkeypatch, spawned, pasta):
    monkeypatch.setenv("AUTOMATION_EDITOR", "idea --wait")

    ss.open_editor(pasta)

    assert spawned == [(["idea", "--wait", pasta], None)]


def test_open_editor_usa_code_ou_o_app_do_vscode_no_mac(monkeypatch, spawned, pasta):
    monkeypatch.delenv("AUTOMATION_EDITOR", raising=False)
    monkeypatch.setattr(ss.shutil, "which", lambda nome: "/usr/local/bin/code")
    ss.open_editor(pasta)

    monkeypatch.setattr(ss.shutil, "which", lambda nome: None)
    monkeypatch.setattr(ss.sys, "platform", "darwin")
    ss.open_editor(pasta)

    assert spawned == [(["code", pasta], None), (["open", "-a", "Visual Studio Code", pasta], None)]


def test_open_editor_sem_nenhum_editor_explica_como_configurar(monkeypatch, spawned, pasta):
    monkeypatch.delenv("AUTOMATION_EDITOR", raising=False)
    monkeypatch.setattr(ss.shutil, "which", lambda nome: None)
    monkeypatch.setattr(ss.sys, "platform", "linux")

    with pytest.raises(GitServiceError, match="AUTOMATION_EDITOR"):
        ss.open_editor(pasta)


@pytest.mark.parametrize("acao", [ss.open_terminal, ss.open_editor])
def test_pasta_inexistente_e_erro(acao, tmp_path):
    with pytest.raises(GitServiceError, match="não existe"):
        acao(str(tmp_path / "nada"))


def test_programa_ausente_vira_erro_claro(monkeypatch, pasta):
    def sem_programa(*args, **kwargs):
        raise FileNotFoundError("open")

    monkeypatch.setattr(ss.subprocess, "Popen", sem_programa)
    monkeypatch.setattr(ss.sys, "platform", "darwin")

    with pytest.raises(GitServiceError, match="não encontrado"):
        ss.open_terminal(pasta)


def test_urls_do_github():
    assert ss.build_repo_web_url("JeanHeberth", "automationBranch") == "https://github.com/JeanHeberth/automationBranch"
    assert (
        ss.build_branch_web_url("o", "r", "feature/minha branch#1")
        == "https://github.com/o/r/tree/feature/minha%20branch%231"
    )
