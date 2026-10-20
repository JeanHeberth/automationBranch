import os

import pytest

pytest.importorskip("customtkinter")

import ui.theme as theme  # noqa: E402


def test_icon_path_e_absoluto_e_existe():
    assert os.path.isabs(theme.ICON_PATH)
    assert os.path.isdir(theme.ICON_PATH)


def test_load_icon_ausente_nao_derruba(monkeypatch):
    monkeypatch.setattr(theme, "_ICON_CACHE", {})
    monkeypatch.setattr(theme.ctk, "CTkImage", lambda **kw: ("stub", kw["size"]))

    icon = theme.load_icon("icone-que-nao-existe.png", size=(10, 10))

    assert icon == ("stub", (10, 10))


def test_load_icon_existente(monkeypatch):
    monkeypatch.setattr(theme, "_ICON_CACHE", {})
    monkeypatch.setattr(theme.ctk, "CTkImage", lambda **kw: "ok")

    assert theme.load_icon("pull.png", size=(12, 12)) == "ok"


def test_load_icon_usa_cache(monkeypatch):
    monkeypatch.setattr(theme, "_ICON_CACHE", {})
    chamadas = {"n": 0}

    def fake_image(**kw):
        chamadas["n"] += 1
        return "img"

    monkeypatch.setattr(theme.ctk, "CTkImage", fake_image)

    theme.load_icon("pull.png", size=(12, 12))
    theme.load_icon("pull.png", size=(12, 12))

    assert chamadas["n"] == 1
