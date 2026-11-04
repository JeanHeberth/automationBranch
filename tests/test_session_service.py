import json
import os
import stat
import sys

import pytest

from services import session_service as ss


class FakeKeyring:
    """Cofre em memória no lugar do Keychain/Credential Locker (os testes nunca tocam o real)."""

    def __init__(self, fail=False):
        self.store = {}
        self.fail = fail

    def get_password(self, service, user):
        if self.fail:
            raise ss.KeyringError("sem cofre")
        return self.store.get((service, user))

    def set_password(self, service, user, token):
        if self.fail:
            raise ss.KeyringError("sem cofre")
        self.store[(service, user)] = token

    def delete_password(self, service, user):
        if self.fail:
            raise ss.KeyringError("sem cofre")
        self.store.pop((service, user), None)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "APP_DIR", tmp_path / "app")
    monkeypatch.setattr(ss, "SESSION_FILE", tmp_path / "app" / "session.json")
    monkeypatch.setattr(ss, "_token_cache", ss._UNSET)
    fake = FakeKeyring()
    monkeypatch.setattr(ss, "keyring", fake)
    return fake


SESSION = {
    "is_authenticated": True,
    "provider": "GitHub",
    "display_name": "Jean",
    "email": "j@x.com",
    "access_token": "segredo",
}


def _file_data():
    return json.loads(ss.SESSION_FILE.read_text(encoding="utf-8"))


def test_sem_arquivo_retorna_sessao_vazia(env):
    session = ss.load_session()

    assert session["is_authenticated"] is False
    assert session["access_token"] is None


def test_token_vai_para_o_cofre_e_nao_para_o_arquivo(env):
    ss.save_session(SESSION)

    assert _file_data()["access_token"] is None
    assert "segredo" not in ss.SESSION_FILE.read_text(encoding="utf-8")
    assert env.store[(ss.KEYRING_SERVICE, ss.KEYRING_USER)] == "segredo"


def test_load_recompõe_o_token_a_partir_do_cofre(env, monkeypatch):
    ss.save_session(SESSION)
    monkeypatch.setattr(ss, "_token_cache", ss._UNSET)  # simula novo início do app

    session = ss.load_session()

    assert session["access_token"] == "segredo"
    assert session["display_name"] == "Jean"


def test_load_usa_cache_e_nao_consulta_o_cofre_de_novo(env):
    ss.save_session(SESSION)
    env.fail = True  # se consultasse o cofre agora, o token se perderia

    assert ss.load_session()["access_token"] == "segredo"


def test_sem_cofre_o_token_fica_no_arquivo(env):
    env.fail = True

    ss.save_session(SESSION)

    assert _file_data()["access_token"] == "segredo"
    assert ss.load_session()["access_token"] == "segredo"


def test_sem_biblioteca_keyring_o_token_fica_no_arquivo(env, monkeypatch):
    monkeypatch.setattr(ss, "keyring", None)

    ss.save_session(SESSION)

    assert _file_data()["access_token"] == "segredo"


@pytest.mark.skipif(sys.platform == "win32", reason="permissões POSIX")
def test_arquivo_so_o_dono_le(env):
    env.fail = True

    ss.save_session(SESSION)

    mode = stat.S_IMODE(os.stat(ss.SESSION_FILE).st_mode)
    assert mode == 0o600


@pytest.mark.skipif(sys.platform == "win32", reason="permissões POSIX")
def test_arquivo_antigo_com_permissao_aberta_e_restringido(env):
    ss.APP_DIR.mkdir(parents=True)
    ss.SESSION_FILE.write_text("{}", encoding="utf-8")
    os.chmod(ss.SESSION_FILE, 0o644)
    env.fail = True

    ss.save_session(SESSION)

    assert stat.S_IMODE(os.stat(ss.SESSION_FILE).st_mode) == 0o600


def test_migra_token_em_texto_puro_para_o_cofre(env):
    ss.APP_DIR.mkdir(parents=True)
    ss.SESSION_FILE.write_text(json.dumps(SESSION), encoding="utf-8")

    session = ss.load_session()

    assert session["access_token"] == "segredo"
    assert env.store[(ss.KEYRING_SERVICE, ss.KEYRING_USER)] == "segredo"
    assert _file_data()["access_token"] is None


def test_migracao_nao_acontece_sem_cofre(env):
    env.fail = True
    ss.APP_DIR.mkdir(parents=True)
    ss.SESSION_FILE.write_text(json.dumps(SESSION), encoding="utf-8")

    assert ss.load_session()["access_token"] == "segredo"
    assert _file_data()["access_token"] == "segredo"


def test_clear_session_apaga_arquivo_e_cofre(env):
    ss.save_session(SESSION)

    ss.clear_session()

    assert not ss.SESSION_FILE.exists()
    assert env.store == {}
    assert ss.load_session()["access_token"] is None


def test_clear_session_sem_nada_nao_falha(env):
    ss.clear_session()


def test_arquivo_corrompido_vira_sessao_vazia(env):
    ss.APP_DIR.mkdir(parents=True)
    ss.SESSION_FILE.write_text("{nao é json", encoding="utf-8")

    assert ss.load_session()["is_authenticated"] is False


@pytest.mark.parametrize(
    "platform, esperado",
    [
        ("darwin", ("Library", "Application Support", "AutomationBranch")),
        ("linux", (".config", "AutomationBranch")),
    ],
)
def test_pasta_de_dados_por_sistema(monkeypatch, tmp_path, platform, esperado):
    monkeypatch.setattr(ss.sys, "platform", platform)
    monkeypatch.setattr(ss.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    assert ss._app_dir() == tmp_path.joinpath(*esperado)


def test_pasta_de_dados_no_windows_usa_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(ss.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    assert ss._app_dir() == tmp_path / "Roaming" / "AutomationBranch"
