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


def test_mouse_na_tela_a_esquerda_usa_a_parte_da_janela_que_esta_la():
    # Janela de -900 a 600; o mouse (x=-400) está na tela da esquerda.
    x, _ = centered_position((-900, 50, 1500, 800), SIZE, SCREEN, pointer=(-400, 300))
    assert x == -900 + (900 - 380) // 2 and x < 0


def test_mouse_na_tela_a_direita_usa_a_parte_da_janela_que_esta_la():
    x, _ = centered_position((1000, 50, 1500, 800), SIZE, SCREEN, pointer=(1800, 300))
    assert x == 1512 + (2500 - 1512 - 380) // 2


def test_mouse_na_tela_principal_mantem_o_comportamento_anterior():
    assert centered_position((-900, 50, 1500, 800), SIZE, SCREEN, pointer=(300, 300)) == \
           centered_position((-900, 50, 1500, 800), SIZE, SCREEN)


from ui.window_position import anchored_position


def test_menu_fica_no_app_mesmo_fora_da_tela_principal():
    # App no monitor da direita (x de 1600 a 3500); a "tela principal" tem 1512 de largura.
    anchor = (3300, 100, 40, 32)
    x, y = anchored_position(anchor, (500, 300), (1600, 0, 3500, 900))
    assert x == 3300 + 40 - 500 and 1600 <= x and x + 500 <= 3500
    assert y == 100 + 32 + 6


def test_menu_fica_no_app_com_coordenadas_negativas():
    x, _ = anchored_position((-200, 100, 40, 32), (500, 300), (-1800, 0, 100, 900))
    assert -1800 <= x and x + 500 <= 100


def test_menu_nao_passa_da_borda_inferior_do_app():
    _, y = anchored_position((100, 800, 40, 32), (500, 300), (0, 0, 1000, 900))
    assert y + 300 <= 900
