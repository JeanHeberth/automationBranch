import sys
import tkinter as tk

from ui.theme import APP_COLORS

# (rótulo do grupo, [(rótulo, chave do handler) ou None para separador])
MENU_SPEC = [
    ("Sincronizar", [
        ("Fetch (todos os remotos, com prune)", "fetch"),
        ("Pull com rebase", "pull_rebase"),
    ]),
    ("Integrar", [
        ("Merge de uma branch na atual…", "merge"),
        ("Rebase na branch…", "rebase"),
        None,
        ("Cherry-pick de um commit…", "cherry_pick"),
        ("Revert de um commit…", "revert"),
    ]),
    ("Desfazer e recuperar", [
        ("Desfazer último commit (mantém as alterações)", "undo_commit"),
        ("Reflog (histórico do HEAD)…", "reflog"),
    ]),
    ("Branches e tags", [
        ("Renomear branch atual…", "rename_branch"),
        ("Limpar branches já mescladas…", "clean_merged"),
        None,
        ("Criar tag…", "new_tag"),
        ("Gerenciar tags…", "manage_tags"),
    ]),
    ("Repositório", [
        ("Abrir repositório no GitHub", "open_repo_web"),
        ("Abrir branch atual no GitHub", "open_branch_web"),
        ("Copiar URL do repositório", "copy_repo_url"),
        None,
        ("Abrir pasta", "open_folder"),
        ("Abrir terminal", "open_terminal"),
        ("Abrir no editor", "open_editor"),
        None,
        ("Clonar repositório…", "clone"),
        ("Inicializar repositório…", "init"),
    ]),
]

OPERATION_NAMES = {"merge": "merge", "rebase": "rebase", "cherry-pick": "cherry-pick", "revert": "revert"}


def handler_keys() -> list[str]:
    return [item[1] for _group, items in MENU_SPEC for item in items if item is not None]


def _style() -> dict:
    # No macOS o menu é nativo e ignora cores; nos demais sistemas acompanha o tema escuro.
    if sys.platform == "darwin":
        return {}
    return {
        "bg": APP_COLORS["panel"],
        "fg": APP_COLORS["text"],
        "activebackground": APP_COLORS["hover"],
        "activeforeground": APP_COLORS["text"],
        "bd": 0,
    }


def build_actions_menu(master, handlers: dict, operation: str | None = None) -> tk.Menu:
    """Menu de ações em grupos. `handlers` mapeia a chave de cada item para um callable.

    Com uma operação parada no meio (conflito), os itens de continuar/abortar vêm primeiro.
    """
    style = _style()
    menu = tk.Menu(master, tearoff=0, **style)

    if operation:
        name = OPERATION_NAMES.get(operation, operation)
        menu.add_command(label=f"Continuar {name} (depois de resolver os conflitos)", command=handlers["continue"])
        menu.add_command(label=f"Abortar {name} em andamento", command=handlers["abort"])
        menu.add_separator()

    for group, items in MENU_SPEC:
        submenu = tk.Menu(menu, tearoff=0, **style)
        for item in items:
            if item is None:
                submenu.add_separator()
                continue
            label, key = item
            submenu.add_command(label=label, command=handlers[key])
        menu.add_cascade(label=group, menu=submenu)

    return menu
