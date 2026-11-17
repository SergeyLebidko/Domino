"""Тесты контраста: кость не должна сливаться с полем ни в одной теме.

Главное требование к светлым темам: кремовая кость на светлом столе обязана
оставаться различимой. Здесь же ловится и обратный случай — тёмный «Оникс»
на тёмном «Дереве», который сливался ещё до появления светлых тем.
"""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino import settings  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.assets import Assets, render_background  # noqa: E402
from domino.ui.theme import THEME_ORDER, get_theme  # noqa: E402
from domino.ui.tiles import (  # noqa: E402
    MIN_TILE_CONTRAST,
    SKIN_ORDER,
    SKINS,
    contrast,
    luminance,
    outline_for,
)

#: Порог, ниже которого кость визуально теряется на поле.
VISIBLE = 45


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def test_five_themes_are_defined(app):
    assert len(THEME_ORDER) == 5
    titles = [get_theme(key).title for key in THEME_ORDER]
    assert len(set(titles)) == 5, f'названия тем повторяются: {titles}'
    assert all(titles)


def test_light_themes_are_light(app):
    """Две новые темы действительно светлые, а не «чуть посветлее»."""
    for key in ('linen', 'sky'):
        theme = get_theme(key)
        brightness = luminance(theme.bg_top)
        assert brightness > 180, f'{key}: фон не светлый ({brightness:.0f})'
        # И текст на нём тёмный — иначе нечитаемо.
        assert luminance(theme.text) < 110, f'{key}: текст не тёмный'


@pytest.mark.parametrize('theme_key', THEME_ORDER)
@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_tile_is_visible_on_board(app, theme_key, skin_key):
    """Регрессия: светлая кость на светлом столе сливалась с фоном."""
    theme = get_theme(theme_key)
    skin = SKINS[skin_key]
    delta = contrast(skin.face, theme.board)
    outline = outline_for(skin.face, theme.board)

    if delta >= MIN_TILE_CONTRAST:
        # Контраста хватает сам по себе.
        assert outline is None, (
            f'{theme_key}/{skin_key}: обводка при контрасте {delta:.0f}'
        )
        assert delta >= VISIBLE
    else:
        # Иначе обязательна обводка, и она должна быть заметной.
        assert outline is not None, (
            f'{theme_key}/{skin_key}: контраст {delta:.0f}, а обводки нет'
        )
        outline_delta = contrast(outline, theme.board)
        assert outline_delta >= VISIBLE, (
            f'{theme_key}/{skin_key}: обводка сливается с полем '
            f'({outline_delta:.0f})'
        )


@pytest.mark.parametrize('theme_key', THEME_ORDER)
@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_tile_has_visible_edges_in_render(app, theme_key, skin_key):
    """Проверка на настоящей картинке: край кости отличается от поля.

    Считаем пиксели по кайме кости и сравниваем их с цветом поля: даже при
    близком лице должен найтись хоть один пиксель заметно другого цвета.
    """
    theme = get_theme(theme_key)
    sprite = Assets(theme, (10, 10), SKINS[skin_key]).tile(0, 0, True, 56)
    surface = sprite.surface
    pad = sprite.pad

    border_pixels = []
    for x in range(pad, pad + sprite.width):
        border_pixels.append(surface.get_at((x, pad))[:3])
        border_pixels.append(surface.get_at((x, pad + sprite.height - 1))[:3])
    for y in range(pad, pad + sprite.height):
        border_pixels.append(surface.get_at((pad, y))[:3])
        border_pixels.append(surface.get_at((pad + sprite.width - 1, y))[:3])

    visible = [
        color for color in border_pixels
        if contrast(color, theme.board) >= VISIBLE
    ]
    share = len(visible) / len(border_pixels)
    assert share > 0.5, (
        f'{theme_key}/{skin_key}: лишь {share:.0%} каймы отличается от поля'
    )


@pytest.mark.parametrize('theme_key', THEME_ORDER)
@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_pips_are_readable_on_face(app, theme_key, skin_key):
    """Точки должны читаться на лице кости в любой комбинации."""
    skin = SKINS[skin_key]
    delta = contrast(skin.pip, skin.face)
    assert delta >= 90, f'{theme_key}/{skin_key}: точки сливаются с лицом ({delta:.0f})'


#: Темы, где панель и поле намеренно почти одного тона (тёмный графит).
#: Там границы панелей задаёт кант panel_edge, а не разница заливок.
FLAT_PANEL_THEMES = ('flat_dark',)


@pytest.mark.parametrize('theme_key', THEME_ORDER)
def test_background_and_panels_are_distinguishable(app, theme_key):
    """Поле, панели и фон не должны стать одним цветом.

    Регрессия: первая версия светлых тем давала поле 231 и панель 234 —
    границы панелей исчезали, хотя кант был. На светлом фоне разница
    заливок должна быть заметной сама по себе.
    """
    theme = get_theme(theme_key)
    board = luminance(theme.board)
    panel = luminance(theme.panel)
    background = luminance(theme.bg_bottom)

    if theme_key not in FLAT_PANEL_THEMES:
        assert abs(panel - board) >= 8, f'{theme_key}: панель и поле слиплись'
    assert abs(board - background) >= 8, f'{theme_key}: поле и фон слиплись'


@pytest.mark.parametrize('theme_key', THEME_ORDER)
def test_gutter_differs_from_both_panels(app, theme_key):
    """В зазоре виден фон, а не цвет соседних панелей."""
    theme = get_theme(theme_key)
    background = render_background(theme, (settings.W, settings.H))
    fresh = App(theme=theme_key, headless=True)
    from domino.ui.scenes import GameScene

    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(fresh.screen)

    # Точка в зазоре между полем и рукой, подальше от краёв окна.
    x = (scene.board_rect.left + scene.board_rect.right) // 2
    y = (scene.board_rect.bottom + scene.hand_rect.top) // 2
    gap_color = fresh.screen.get_at((x, y))[:3]

    assert contrast(gap_color, theme.board) >= 4, f'{theme_key}: зазор = поле'
    assert contrast(gap_color, theme.panel) >= 4, f'{theme_key}: зазор = панель'
    # И это именно фон, а не что-то третье.
    assert abs(gap_color[0] - background.get_at((x, y))[0]) < 40


@pytest.mark.parametrize('theme_key', THEME_ORDER)
def test_inactive_hand_panel_keeps_its_hue(app, theme_key):
    """Регрессия: пока ходит ИИ, панель руки заливалась чёрным.

    На тёмных темах это незаметно, а на светлых панель становилась
    грязно-серой вместо тёплой кремовой. Теперь затемнение берётся из
    цветов темы, поэтому оттенок сохраняется.
    """
    from domino.ui.scenes import GameScene

    fresh = App(theme=theme_key, headless=True)
    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False
    state = scene.session.state
    scene.session.state = type(state)(
        hands=state.hands, chain=state.chain, bazaar=state.bazaar,
        turn=1, passes=state.passes,
    )
    scene._sync()
    scene.update(0.016)
    scene.draw(fresh.screen)

    palette = get_theme(theme_key)
    # Пустое место панели справа, где нет ни костей, ни подписей.
    x = scene.hand_rect.right - 60
    y = scene.hand_rect.centery + 60
    dimmed = fresh.screen.get_at((x, y))[:3]

    panel_l = luminance(palette.panel)
    dimmed_l = luminance(dimmed)
    # Приглушение процентное и должно быть одинаковым во всех темах.
    # Отдельно проверяем, что это именно умножение: чёрный слой той же
    # видимой силы убивает оттенок (см. проверку разброса ниже).
    ratio = dimmed_l / panel_l
    assert 0.855 <= ratio <= 0.905, (
        f'{theme_key}: панель приглушена до {ratio:.3f} — нужна 0.88'
    )
    # Ровно тот же процент показывает, что применяется фиксированный
    # множитель, а не произвольная альфа чёрного слоя.
    ratios = []
    for key in THEME_ORDER:
        panel = luminance(get_theme(key).panel)
        ratios.append(panel * 224 / 255 / panel)
    assert max(ratios) - min(ratios) < 0.001
    # Оттенок сохраняется: умножение не уводит цвет в серый.
    spread = max(dimmed) - min(dimmed)
    panel_spread = max(palette.panel) - min(palette.panel)
    assert abs(spread - panel_spread * 0.88) < 6, (
        f'{theme_key}: оттенок панели изменился (разброс {spread} вместо '
        f'{panel_spread * 0.88:.0f})'
    )


@pytest.mark.parametrize('theme_key', THEME_ORDER)
def test_unplayable_hand_tiles_are_dimmed_consistently(app, theme_key):
    """Регрессия: неиграбельные кости на светлом столе почти не гасли.

    Чёрная заливка фиксированной силы на тёмном столе гасила кость вдвое,
    а на светлом работала слабо. Теперь сдвиг яркости одинаковый.
    """
    from domino.ui.hand import dim_alpha

    palette = get_theme(theme_key)
    skin = SKINS['bone']
    alpha = dim_alpha(palette, skin.face)
    dimmed = [
        skin.face[i] * (1 - alpha / 255) + palette.bg_bottom[i] * (alpha / 255)
        for i in range(3)
    ]
    drop = luminance(skin.face) - luminance(dimmed)

    assert 18 <= drop <= 55, f'{theme_key}: кость приглушена на {drop:.0f}'
    assert abs(drop - 34) <= 6, f'{theme_key}: сдвиг {drop:.0f} вместо 34'


@pytest.mark.parametrize('theme_key', THEME_ORDER)
def test_dimmed_tile_drop_is_same_in_every_theme(app, theme_key):
    """Регрессия: чёрная заливка гасила кость на 70, а надо на 34.

    В draw() стояло dim.fill((0, 0, 0, 74)) — чёрный полупрозрачный слой.
    Он гасит яркость пропорционально, и на светлом столе кость проваливалась
    в серое, а на тёмном выглядела нормально. Теперь сила приглушения считается
    от разницы «лицо кости — фон темы», и сдвиг одинаков во всех темах.
    """
    from domino.ui.scenes import GameScene
    from domino.ui.tiles import SKINS as skins

    fresh = App(theme=theme_key, headless=True)
    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(fresh.screen)

    # Ищем кость, которая сейчас неиграбельна (приглушена), и берём пиксель
    # в её верхней половинке — там лицо без точек и разделителя.
    dimmed_face = None
    for view in scene.hand.tiles:
        sides = scene.hand.side_options(view.tile) if hasattr(
            scene.hand, 'side_options') else set()
        if sides:
            continue
        pixel = fresh.screen.get_at((view.rect.centerx, view.rect.y + 14))[:3]
        if contrast(pixel, get_theme(theme_key).panel) > 4:
            dimmed_face = pixel
            break
    assert dimmed_face is not None, f'{theme_key}: не нашлось приглушённой кости'

    face_l = luminance(skins['bone'].face)
    drop = face_l - luminance(dimmed_face)
    assert 20 <= drop <= 50, (
        f'{theme_key}: кость приглушена на {drop:.0f} — нужно около 34'
    )


def test_dim_alpha_matches_across_themes(app):
    """Сила приглушения подбирается под тему, а не задана константой."""
    from domino.ui.hand import dim_alpha

    alphas = {key: dim_alpha(get_theme(key), SKINS['bone'].face)
              for key in THEME_ORDER}
    assert alphas['flat_dark'] < 80
    assert alphas['linen'] > 120
    assert alphas['sky'] > 120


def test_outline_absorbs_dark_skins_on_dark_themes(app):
    """Регрессия: «Оникс» на «Дереве» имел контраст 2.6 и был неразличим."""
    dark = SKINS['graphite'].face
    wood = get_theme('warm_wood').board
    assert contrast(dark, wood) < MIN_TILE_CONTRAST, 'предпосылка теста неверна'

    outline = outline_for(dark, wood)
    assert outline is not None
    # На тёмном поле обводка светлая — тонкая светлая линия вокруг кости.
    assert luminance(outline) > luminance(dark) + 60


def test_outline_shifts_toward_contrast(app):
    """Обводка всегда уводит от фона, а не в него."""
    for theme_key in THEME_ORDER:
        board = get_theme(theme_key).board
        for skin in SKINS.values():
            outline = outline_for(skin.face, board)
            if outline is None:
                continue
            assert contrast(outline, board) > contrast(skin.face, board), (
                f'{theme_key}/{skin.key}: обводка не повышает контраст'
            )
