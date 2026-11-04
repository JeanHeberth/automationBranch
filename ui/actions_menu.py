# Conteúdo do painel de ações: (grupo, [(rótulo, chave do handler, ícone)]).
# É a fonte única: o painel desenha a partir daqui e o controlador precisa ter um handler
# para cada chave (um teste garante isso).
#
# O painel complementa a barra de cima, não a repete: Undo, Redo, Pull, Terminal e "Abrir"
# (escolher repositório) ficam só lá.
# Cada ação aparece uma vez (criar tag fica dentro de "Gerenciar tags").
MENU_SPEC = [
    ("Sincronizar", [
        ("Fetch (com prune)", "fetch", "refresh.png"),
        ("Pull com rebase", "pull_rebase", "pull.png"),
    ]),
    ("Integrar", [
        ("Merge de uma branch…", "merge", "merge_pr.png"),
        ("Rebase na branch…", "rebase", "branch.png"),
        ("Cherry-pick de um commit…", "cherry_pick", "cherry.png"),
        ("Revert de um commit…", "revert", "revert.png"),
    ]),
    ("Branches, tags e histórico", [
        ("Renomear branch atual…", "rename_branch", "edit.png"),
        ("Limpar branches mescladas…", "clean_merged", "delete_branch.png"),
        ("Gerenciar tags…", "manage_tags", "tag.png"),
        ("Reflog (histórico do HEAD)…", "reflog", "history.png"),
    ]),
    ("Repositório", [
        ("Abrir repositório no GitHub", "open_repo_web", "external.png"),
        ("Abrir branch no GitHub", "open_branch_web", "external.png"),
        ("Copiar URL do repositório", "copy_repo_url", "copy.png"),
        ("Abrir no editor", "open_editor", "code.png"),
        ("Clonar repositório…", "clone", "clone.png"),
        ("Inicializar repositório…", "init", "folder_plus.png"),
    ]),
]

# Quais grupos ficam em cada coluna do painel (índices de MENU_SPEC).
COLUMNS = ((0, 1, 2), (3,))

OPERATION_NAMES = {"merge": "merge", "rebase": "rebase", "cherry-pick": "cherry-pick", "revert": "revert"}


def handler_keys() -> list[str]:
    return [key for _group, items in MENU_SPEC for _label, key, _icon in items]
