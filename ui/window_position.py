"""Posiciona janelas filhas sobre a janela principal, mesmo com várias telas (ex.: iPad como
tela estendida). O Tk só informa o tamanho da tela principal, então a janela principal pode
estar parcial ou totalmente fora dela (coordenadas negativas ou além da largura)."""

import re

BOTTOM_MARGIN = 60  # Dock / barra de tarefas


def _axis_start(master_start: int, master_len: int, size: int, screen_len: int,
                offset: int | None = None, margin: int = 0, pointer: int | None = None) -> int:
    master_end = master_start + master_len

    # O mouse está fora da tela principal (ex.: no iPad): é lá que o usuário está olhando.
    # Usa a parte da janela principal que fica desse lado.
    if pointer is not None and (pointer < 0 or pointer >= screen_len):
        lo, hi = (master_start, min(master_end, 0)) if pointer < 0 else (max(master_start, screen_len), master_end)
        if hi > lo:
            return lo + (hi - lo - size) // 2 if offset is None else lo + offset

    lo = max(master_start, 0)
    hi = min(master_start + master_len, screen_len)

    if hi <= lo:
        # A janela principal está inteira em outra tela: centraliza nela, sem limitar à principal.
        if offset is not None:
            return master_start + offset
        return master_start + (master_len - size) // 2

    # Centraliza na parte da janela principal que aparece na tela principal.
    if offset is None:
        start = lo + (hi - lo - size) // 2
    else:
        start = lo + offset
    return max(0, min(start, screen_len - size - margin))


def centered_position(master_box: tuple, size: tuple, screen: tuple, top_offset: int | None = None,
                      pointer: tuple | None = None):
    """master_box = (x, y, largura, altura); size e screen = (largura, altura);
    pointer = (x, y) do mouse, quando conhecido."""
    mx, my, mw, mh = master_box
    width, height = size
    screen_w, screen_h = screen
    px, py = pointer if pointer else (None, None)
    x = _axis_start(mx, mw, width, screen_w, pointer=px)
    y = _axis_start(my, mh, height, screen_h, offset=top_offset, margin=BOTTOM_MARGIN, pointer=py)
    return x, y


def _window_size(window) -> tuple:
    """Tamanho definido por geometry(); janela oculta (withdraw) informa winfo_width = 1."""
    match = re.match(r"(\d+)x(\d+)", window.geometry())
    if match and int(match.group(1)) > 1:
        return int(match.group(1)), int(match.group(2))
    return window.winfo_reqwidth(), window.winfo_reqheight()


def center_on_master(window, master, top_offset: int | None = None):
    """Posiciona a janela e só então a exibe.

    A janela deve ter sido ocultada (`withdraw`) na criação: ao aparecer no tamanho padrão (200x200)
    e depois ser movida, o macOS (principalmente em tela estendida, como o iPad) deixa uma
    "sombra" preta parada na tela."""
    window.update_idletasks()
    x, y = centered_position(
        (master.winfo_rootx(), master.winfo_rooty(), master.winfo_width(), master.winfo_height()),
        _window_size(window),
        (window.winfo_screenwidth(), window.winfo_screenheight()),
        top_offset,
        pointer=window.winfo_pointerxy(),
    )
    window.geometry(f"+{x}+{y}")
    window.deiconify()

def anchored_position(anchor_box: tuple, size: tuple, bounds: tuple, gap: int = 6, margin: int = 8):
    """Posição de um menu flutuante abaixo do botão, com a borda direita alinhada à dele.

    O limite é a janela do app (`bounds` = esquerda, topo, direita, base), e não a tela: o Tk
    só conhece a tela principal, e limitar a ela jogava o menu para o monitor errado quando o
    app estava em outro (Mac, iPad ou monitor externo)."""
    ax, ay, aw, ah = anchor_box
    width, height = size
    left, top, right, bottom = bounds

    x = ax + aw - width
    y = ay + ah + gap

    x = max(left + margin, min(x, right - width - margin))
    y = max(top + margin, min(y, bottom - height - margin))
    return x, y


def place_below_anchor(window, anchor_widget):
    window.update_idletasks()
    app = anchor_widget.winfo_toplevel()
    x, y = anchored_position(
        (anchor_widget.winfo_rootx(), anchor_widget.winfo_rooty(),
         anchor_widget.winfo_width(), anchor_widget.winfo_height()),
        (window.winfo_reqwidth(), window.winfo_reqheight()),
        (app.winfo_rootx(), app.winfo_rooty(),
         app.winfo_rootx() + app.winfo_width(), app.winfo_rooty() + app.winfo_height()),
    )
    window.geometry(f"+{x}+{y}")
