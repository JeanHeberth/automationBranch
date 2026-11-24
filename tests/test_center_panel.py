from ui.center_panel import build_commit_tooltip_text


def test_tooltip_do_commit_lista_refs_e_tipo_merge():
    texto = build_commit_tooltip_text(
        {
            "hash": "abc1234",
            "subject": "Merge pull request #1",
            "author": "Fulano",
            "decorations": "(HEAD -> main, origin/main)",
            "is_merge": True,
        }
    )

    assert texto.splitlines() == [
        "Refs: main, origin/main",
        "Commit: abc1234",
        "Autor: Fulano",
        "Mensagem: Merge pull request #1",
        "Tipo: Merge commit",
    ]


def test_tooltip_do_commit_sem_refs():
    texto = build_commit_tooltip_text({"hash": "abc1234", "subject": "x", "author": "y"})

    assert texto.splitlines()[0] == "Commit: abc1234"
    assert "Tipo" not in texto
