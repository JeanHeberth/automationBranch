"""Posiciona janelas filhas sobre a janela principal, mesmo com várias telas (ex.: iPad como
tela estendida). O Tk só informa o tamanho da tela principal, então a janela principal pode
estar parcial ou totalmente fora dela (coordenadas negativas ou além da largura)."""

BOTTOM_MARGIN = 60  # Dock / barra de tarefas


def _axis_start(master_start: int, master_len: int, size: int, screen_len: int,
                offset: int | None = None, margin: int = 0) -> int:
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


def centered_position(master_box: tuple, size: tuple, screen: tuple, top_offset: int | None = None):
    """master_box = (x, y, largura, altura); size e screen = (largura, altura)."""
    mx, my, mw, mh = master_box
    width, height = size
    screen_w, screen_h = screen
    x = _axis_start(mx, mw, width, screen_w)
    y = _axis_start(my, mh, height, screen_h, offset=top_offset, margin=BOTTOM_MARGIN)
    return x, y


def center_on_master(window, master, top_offset: int | None = None):
    window.update_idletasks()
    x, y = centered_position(
        (master.winfo_rootx(), master.winfo_rooty(), master.winfo_width(), master.winfo_height()),
        (window.winfo_width(), window.winfo_height()),
        (window.winfo_screenwidth(), window.winfo_screenheight()),
        top_offset,
    )
    window.geometry(f"+{x}+{y}")
