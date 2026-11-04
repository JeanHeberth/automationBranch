from ui.window_position import centered_position

SCREEN = (1512, 982)
SIZE = (380, 200)


def test_janela_inteira_na_tela_centraliza():
    assert centered_position((100, 100, 1000, 700), SIZE, SCREEN) == (410, 350)


def test_janela_esticada_para_tela_a_esquerda_centraliza_na_parte_visivel():
    # Janela começa 900 px à esquerda da tela principal; só 600 px dela aparecem.
    x, y = centered_position((-900, 50, 1500, 800), SIZE, SCREEN)
    assert 0 <= x and x + SIZE[0] <= 600
    assert y == 350


def test_janela_esticada_para_tela_a_direita_fica_dentro_da_principal():
    x, _ = centered_position((1000, 50, 1500, 800), SIZE, SCREEN)
    assert 1000 <= x and x + SIZE[0] <= SCREEN[0]


def test_janela_inteira_em_outra_tela_centraliza_nela_sem_limitar_a_zero():
    x, _ = centered_position((-2000, 100, 1200, 700), SIZE, SCREEN)
    assert x == -2000 + (1200 - 380) // 2 and x < 0


def test_top_offset_e_limitado_pela_borda_inferior():
    _, y = centered_position((0, 0, 1000, 982), (620, 560), SCREEN, top_offset=900)
    assert y + 560 <= SCREEN[1] - 60
