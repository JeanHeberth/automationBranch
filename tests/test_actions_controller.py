import pytest

pytest.importorskip("customtkinter")

from services.git_runner import GitServiceError  # noqa: E402
from ui import actions_controller as ac  # noqa: E402
from ui.actions_menu import MENU_SPEC, handler_keys  # noqa: E402


class FakeWindow:
    """Janela principal mínima: roda o trabalho em segundo plano de forma síncrona."""

    selected_repo_path = "/repo"

    def __init__(self):
        self.statuses, self.errors, self.selected = [], [], []
        self.synced = 0

    def _run_in_background(self, work, on_success, *, busy_message, error_title, error_status):
        try:
            result = work()
        except Exception as exc:
            self.errors.append((error_title, str(exc)))
            return
        on_success(result)

    def set_status(self, text):
        self.statuses.append(text)

    def sync_branch_ui(self, *args):
        self.synced += 1

    def select_repository(self, folder):
        self.selected.append(folder)


class Dialogs:
    """Substitui as caixas de diálogo e registra o que foi mostrado."""

    def __init__(self, monkeypatch, yes=True):
        self.yes = yes
        self.calls = []
        for name in ("showinfo", "showwarning", "showerror"):
            monkeypatch.setattr(ac.messagebox, name, lambda title, text, _n=name, **kw: self.calls.append((_n, title, text)))
        monkeypatch.setattr(ac.messagebox, "askyesno", self._ask)

    def _ask(self, title, text, **kwargs):
        self.calls.append(("askyesno", title, text))
        return self.yes

    def kinds(self):
        return [call[0] for call in self.calls]


@pytest.fixture
def window():
    return FakeWindow()


@pytest.fixture
def controller(window):
    return ac.ActionsController(window)


# ---------- ligação menu <-> controlador ----------

def test_todo_item_do_menu_tem_handler(controller):
    handlers = controller.handlers()

    assert set(handler_keys()) <= set(handlers)
    assert {"continue", "abort"} <= set(handlers)
    assert all(callable(handler) for handler in handlers.values())


def test_menu_nao_tem_chaves_repetidas():
    keys = handler_keys()
    assert len(keys) == len(set(keys))
    assert [group for group, _items in MENU_SPEC] == [
        "Sincronizar", "Integrar", "Branches, tags e histórico", "Repositório",
    ]


def test_painel_nao_repete_o_que_a_barra_de_cima_ja_tem():
    # Undo, Redo e Terminal são botões do topo; o painel não deve oferecê-los de novo.
    assert not {"undo_commit", "redo_commit", "open_terminal", "open_folder"} & set(handler_keys())


def test_cada_acao_aparece_uma_so_vez_no_painel():
    labels = [label for _group, items in MENU_SPEC for label, _key, _icon in items]
    assert len(labels) == len(set(labels))
    # criar tag mora dentro de "Gerenciar tags"
    assert "new_tag" not in handler_keys()


def test_todo_icone_do_menu_existe():
    import os
    import ui.theme as theme

    for _group, items in MENU_SPEC:
        for _label, key, icon in items:
            assert os.path.exists(os.path.join(theme.ICON_PATH, icon)), f"{key}: falta {icon}"


def test_painel_distribui_todos_os_grupos_em_colunas():
    from ui.actions_menu import COLUMNS

    usados = sorted(index for column in COLUMNS for index in column)
    assert usados == list(range(len(MENU_SPEC)))


def test_acoes_sem_repositorio_avisam_e_nao_executam(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch)
    window.selected_repo_path = None
    chamado = []
    monkeypatch.setattr(ac.git_actions, "fetch_all", lambda repo: chamado.append(repo))

    for key in ("fetch", "merge", "reflog", "open_editor", "cherry_pick"):
        controller.handlers()[key]()
    # Undo, Redo, Terminal e "nova tag" não estão no painel: botões do topo e a janela de tags
    # chamam estes métodos diretamente.
    controller.undo_commit()
    controller.redo_commit()
    controller.open_terminal()
    controller.new_tag()

    assert chamado == []
    assert dialogs.kinds() == ["showwarning"] * 9


# ---------- operações que podem conflitar ----------

def test_integracao_com_sucesso_atualiza_e_mostra_o_resultado(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch)

    controller._integrate("/repo", lambda: "Merge made by 'ort'.", "Merge concluído.", "Merge", "...")

    assert window.synced == 1 and window.statuses == ["Merge concluído."]
    assert dialogs.calls == [("showinfo", "Merge", "Merge made by 'ort'.")]


def test_integracao_conflito_oferece_abortar_e_aborta(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch, yes=True)
    monkeypatch.setattr(ac.git_actions, "get_operation_in_progress", lambda repo: "merge")
    abortadas = []
    monkeypatch.setattr(ac.git_actions, "abort_operation", lambda repo: abortadas.append(repo))

    def conflita():
        raise GitServiceError("CONFLICT (content): Merge conflict in f.txt")

    controller._integrate("/repo", conflita, "ok", "Merge", "...")

    assert dialogs.kinds() == ["askyesno"]
    assert "CONFLICT" in dialogs.calls[0][2] and "Continuar merge" in dialogs.calls[0][2]
    assert abortadas == ["/repo"]
    assert window.statuses[-1] == "Operação abortada."


def test_integracao_conflito_recusando_abortar_mantem_a_operacao(monkeypatch, controller, window):
    Dialogs(monkeypatch, yes=False)
    monkeypatch.setattr(ac.git_actions, "get_operation_in_progress", lambda repo: "rebase")
    abortadas = []
    monkeypatch.setattr(ac.git_actions, "abort_operation", lambda repo: abortadas.append(repo))

    controller._integrate("/repo", lambda: (_ for _ in ()).throw(GitServiceError("x")), "ok", "Rebase", "...")

    assert abortadas == []
    assert "parou em conflito" in window.statuses[-1]


def test_integracao_erro_sem_operacao_pendente_vira_erro_normal(monkeypatch, controller, window):
    Dialogs(monkeypatch)
    monkeypatch.setattr(ac.git_actions, "get_operation_in_progress", lambda repo: None)

    controller._integrate("/repo", lambda: (_ for _ in ()).throw(GitServiceError("branch inexistente")), "ok", "Merge", "...")

    assert window.errors == [("Erro: Merge", "branch inexistente")]
    assert window.synced == 0


def test_branch_options_exclui_atual_e_remotas_duplicadas():
    options = ac.ActionsController._branch_options(
        ["main", "feature/a"], ["origin/main", "origin/feature/b", "origin/feature/a"], exclude="main"
    )

    assert options == ["feature/a", "origin/feature/b"]


# ---------- proteções ----------

def test_rebase_em_branch_protegida_e_bloqueado_antes_de_perguntar(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "develop")
    monkeypatch.setattr(ac, "get_local_and_remote_branches", lambda repo: (["develop", "main"], []))
    chamado = []
    monkeypatch.setattr(ac.git_actions, "rebase_onto", lambda *a: chamado.append(a))

    controller.rebase()

    assert dialogs.kinds() == ["showwarning"] and "protegida" in dialogs.calls[0][2]
    assert chamado == []


def test_merge_sem_outra_branch_informa(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(ac, "get_local_and_remote_branches", lambda repo: (["feature/x"], ["origin/feature/x"]))

    controller.merge()

    assert dialogs.calls == [("showinfo", "Merge", "Não há outra branch para mesclar.")]


def test_desfazer_commit_em_branch_protegida_e_bloqueado(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "main")
    chamado = []
    monkeypatch.setattr(ac.git_actions, "undo_last_commit", lambda repo: chamado.append(repo))

    controller.undo_commit()

    assert dialogs.kinds() == ["showwarning"] and chamado == []


def test_desfazer_commit_ja_enviado_avisa_do_force_push(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch, yes=True)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(ac, "is_last_commit_pushed", lambda repo, branch: True)
    monkeypatch.setattr(ac.git_actions, "get_last_commit_summary", lambda repo: "abc123 meu commit")
    monkeypatch.setattr(ac.git_actions, "undo_last_commit", lambda repo: "abc123 meu commit")

    controller.undo_commit()

    assert "force push" in dialogs.calls[0][2] and "abc123 meu commit" in dialogs.calls[0][2]
    assert window.statuses[-1] == "Commit desfeito: abc123 meu commit"


def test_desfazer_commit_recusado_nao_executa(monkeypatch, controller):
    Dialogs(monkeypatch, yes=False)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(ac, "is_last_commit_pushed", lambda repo, branch: False)
    monkeypatch.setattr(ac.git_actions, "get_last_commit_summary", lambda repo: "x")
    chamado = []
    monkeypatch.setattr(ac.git_actions, "undo_last_commit", lambda repo: chamado.append(repo))

    controller.undo_commit()

    assert chamado == []


def test_renomear_branch_protegida_nem_pergunta_o_nome(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "main")
    perguntou = []
    monkeypatch.setattr(ac, "ask_string", lambda *a, **k: perguntou.append(a))

    controller.rename_branch()

    assert dialogs.kinds() == ["showwarning"] and perguntou == []


# ---------- refazer ----------

def test_refazer_traz_o_commit_desfeito(monkeypatch, controller, window):
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(ac.git_actions, "get_redo_target", lambda repo: {"hash": "abc", "summary": "abc meu commit"})
    monkeypatch.setattr(ac.git_actions, "redo_last_undo", lambda repo: "abc meu commit")

    controller.redo_commit()

    assert window.statuses[-1] == "Commit refeito: abc meu commit"
    assert window.synced == 1


def test_refazer_sem_desfazer_recente_orienta_para_o_reflog(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(ac.git_actions, "get_redo_target", lambda repo: None)
    chamado = []
    monkeypatch.setattr(ac.git_actions, "redo_last_undo", lambda repo: chamado.append(repo))

    controller.redo_commit()

    assert chamado == [] and dialogs.kinds() == ["showinfo"] and "Reflog" in dialogs.calls[0][2]


def test_refazer_em_branch_protegida_e_bloqueado(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "develop")
    chamado = []
    monkeypatch.setattr(ac.git_actions, "redo_last_undo", lambda repo: chamado.append(repo))

    controller.redo_commit()

    assert dialogs.kinds() == ["showwarning"] and chamado == []


# ---------- limpar branches ----------

def test_limpar_branches_apaga_as_confirmadas_e_relata_falhas(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch, yes=True)
    monkeypatch.setattr(ac, "get_local_and_remote_branches", lambda repo: (["main", "feature/a", "feature/b"], []))
    monkeypatch.setattr(ac.git_actions, "get_merged_branches", lambda repo, base: ["feature/a", "feature/b"])

    def apagar(repo, name):
        if name == "feature/b":
            raise GitServiceError("falhou")

    monkeypatch.setattr(ac, "delete_local_branch", apagar)

    controller.clean_merged()

    assert "askyesno" in dialogs.kinds() and "feature/a" in dialogs.calls[0][2]
    assert window.statuses[-1] == "1 branch(es) removida(s)."
    assert dialogs.calls[-1][0] == "showwarning" and "feature/b: falhou" in dialogs.calls[-1][2]


def test_limpar_branches_sem_nada_mesclado_informa(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac, "get_local_and_remote_branches", lambda repo: (["main"], []))
    monkeypatch.setattr(ac.git_actions, "get_merged_branches", lambda repo, base: [])

    controller.clean_merged()

    assert dialogs.kinds() == ["showinfo"] and "Nenhuma branch" in dialogs.calls[0][2]


# ---------- repositório ----------

def test_abrir_no_editor_mostra_erro_do_sistema(monkeypatch, controller):
    dialogs = Dialogs(monkeypatch)

    def falha(path):
        raise GitServiceError("A pasta não existe")

    monkeypatch.setattr(ac.system, "open_editor", falha)

    controller.open_editor()

    assert dialogs.calls == [("showerror", "Erro", "A pasta não existe")]


def test_clonar_seleciona_o_repositorio_clonado(monkeypatch, controller, window):
    monkeypatch.setattr(ac, "ask_string", lambda *a, **k: "https://github.com/o/r.git")
    monkeypatch.setattr(ac.filedialog, "askdirectory", lambda **k: "/destino")
    monkeypatch.setattr(ac.git_actions, "clone_repository", lambda url, parent: f"{parent}/r")

    controller.clone()

    assert window.selected == ["/destino/r"]


def test_clonar_cancelado_em_qualquer_etapa_nao_faz_nada(monkeypatch, controller, window):
    clonados = []
    monkeypatch.setattr(ac.git_actions, "clone_repository", lambda *a: clonados.append(a))

    monkeypatch.setattr(ac, "ask_string", lambda *a, **k: None)
    controller.clone()

    monkeypatch.setattr(ac, "ask_string", lambda *a, **k: "url")
    monkeypatch.setattr(ac.filedialog, "askdirectory", lambda **k: "")
    controller.clone()

    assert clonados == [] and window.selected == []


def test_inicializar_pasta_que_ja_e_repositorio_apenas_seleciona(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch)
    monkeypatch.setattr(ac.filedialog, "askdirectory", lambda **k: "/ja/repo")
    monkeypatch.setattr(ac, "is_git_repository", lambda folder: True)
    iniciados = []
    monkeypatch.setattr(ac.git_actions, "init_repository", lambda f: iniciados.append(f))

    controller.init_repo()

    assert iniciados == [] and window.selected == ["/ja/repo"] and dialogs.kinds() == ["showinfo"]


def test_inicializar_pasta_nova_confirma_e_seleciona(monkeypatch, controller, window):
    Dialogs(monkeypatch, yes=True)
    monkeypatch.setattr(ac.filedialog, "askdirectory", lambda **k: "/nova")
    monkeypatch.setattr(ac, "is_git_repository", lambda folder: False)
    monkeypatch.setattr(ac.git_actions, "init_repository", lambda f: f)

    controller.init_repo()

    assert window.selected == ["/nova"]


def test_copiar_url_usa_a_area_de_transferencia(monkeypatch, controller, window):
    window.clipboard = []
    window.clipboard_clear = lambda: window.clipboard.clear()
    window.clipboard_append = window.clipboard.append
    monkeypatch.setattr(ac, "get_repo_owner_and_name", lambda repo: ("o", "r"))

    controller.copy_repo_url()

    assert window.clipboard == ["https://github.com/o/r"]


def test_abrir_branch_no_github_monta_o_link_da_branch(monkeypatch, controller, window):
    abertas = []
    monkeypatch.setattr(ac, "get_repo_owner_and_name", lambda repo: ("o", "r"))
    monkeypatch.setattr(ac, "get_current_branch", lambda repo: "feature/x")
    monkeypatch.setattr(ac.webbrowser, "open", abertas.append)

    controller.open_branch_web()

    assert abertas == ["https://github.com/o/r/tree/feature/x"]


# ---------- tags ----------

def test_apagar_tag_remota_pede_confirmacao(monkeypatch, controller, window):
    dialogs = Dialogs(monkeypatch, yes=False)
    apagadas = []
    monkeypatch.setattr(ac.git_actions, "delete_remote_tag", lambda repo, name: apagadas.append(name))

    controller._tag_action("delete_remote", "v1")
    assert apagadas == [] and dialogs.kinds() == ["askyesno"]

    dialogs.yes = True
    controller._tag_action("delete_remote", "v1")
    assert apagadas == ["v1"] and window.statuses[-1] == "Tag 'v1' apagada do remoto."


def test_nova_tag_cancelada_no_nome_ou_na_mensagem(monkeypatch, controller):
    criadas = []
    monkeypatch.setattr(ac.git_actions, "create_tag", lambda *a: criadas.append(a))

    monkeypatch.setattr(ac, "ask_string", lambda *a, **k: None)
    controller.new_tag()

    respostas = iter(["v1", None])
    monkeypatch.setattr(ac, "ask_string", lambda *a, **k: next(respostas))
    controller.new_tag()

    assert criadas == []
