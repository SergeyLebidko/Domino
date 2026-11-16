"""Тесты мини-карты: заливка обязана оставаться внутри скруглённого контура."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.settings import MINIMAP_H  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402
from domino.ui.theme import THEME_ORDER  # noqa: E402

RADIUS = MINIMAP_H // 2


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _scene(app):
    """Сцена с длинной цепочкой в идущей (не завершённой) партии."""
    import random

    scene = GameScene(app)
    scene.session.enable_ai = False
    rng = random.Random(3)
    # Останавливаемся, когда цепочка уже длинная, но партия продолжается:
    # затемнение итогов иначе изменит цвета на снимке.
    for _ in range(200):
        state = scene.session.state
        if scene.session.is_over:
            break
        if len(state.chain) >= 14 and len(state.hands[0]) >= 3:
            break
        if len(state.hands[state.turn]) <= 1:
            break
        moves = state.legal_moves(state.turn)
        if not moves:
            if state.bazaar:
                scene.session.draw_tile()
                scene._sync()
                continue
            break
        scene.session.play_move(moves[rng.randrange(len(moves))])
        scene._sync()

    scene.result_shown = False
    scene.board.center_all()
    scene.board.camera = scene.board.target_camera
    scene.update(0.016)
    return scene


def _bar(scene) -> pg.Rect:
    rect = scene.board_rect
    return pg.Rect(rect.left + 40, rect.bottom - MINIMAP_H - 20,
                   rect.width - 80, MINIMAP_H)


def _fill_colors(scene):
    palette = scene.ctx.palette
    return {palette.player, palette.ai, palette.text_dim}


def _is_fill(pixel, colors) -> bool:
    return any(
        all(abs(pixel[i] - color[i]) < 14 for i in range(3))
        for color in colors
    )


def _inside_rounded(x: int, y: int, width: int, height: int, radius: int) -> bool:
    """Точка внутри скруглённого прямоугольника (по дугам в углах).

    Граница — настоящая дуга радиуса ``radius``; всё, что ближе к центру
    угла, визуально уже за контуром и является дефектом.
    """
    cx = radius if x < radius else (width - radius - 1 if x > width - radius - 1 else None)
    cy = radius if y < radius else (height - radius - 1 if y > height - radius - 1 else None)
    if cx is None or cy is None:
        return True
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_minimap_fill_does_not_escape_rounded_corners(app, theme):
    """Регрессия: цветные сегменты вылезали за скруглённые торцы полосы."""
    app.ctx.set_theme(theme)
    scene = _scene(app)
    scene.draw(app.screen)

    bar = _bar(scene)
    colors = _fill_colors(scene)

    leaks = []
    for y in range(bar.height):
        for x in range(bar.width):
            if not _is_fill(app.screen.get_at((bar.x + x, bar.y + y)), colors):
                continue
            if not _inside_rounded(x, y, bar.width, bar.height, RADIUS):
                leaks.append((x, y))

    assert not leaks, f'{theme}: заливка вышла за скругление в {leaks[:8]}'


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_minimap_corners_are_background(app, theme):
    """Углы полосы должны оставаться фоном панели, а не заливкой."""
    app.ctx.set_theme(theme)
    scene = _scene(app)
    scene.draw(app.screen)

    bar = _bar(scene)
    colors = _fill_colors(scene)
    corners = [
        (bar.left + 1, bar.top + 1),
        (bar.right - 2, bar.top + 1),
        (bar.left + 1, bar.bottom - 2),
        (bar.right - 2, bar.bottom - 2),
    ]
    for point in corners:
        pixel = app.screen.get_at(point)
        assert not _is_fill(pixel, colors), f'{theme}: заливка в углу {point}: {pixel}'


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_minimap_border_survives_fill(app, theme):
    """Рамка полосы видна поверх заливки по всей длине."""
    app.ctx.set_theme(theme)
    scene = _scene(app)
    scene.draw(app.screen)

    bar = _bar(scene)
    palette = scene.ctx.palette
    mismatches = 0
    for x in range(bar.left + RADIUS, bar.right - RADIUS, 17):
        pixel = app.screen.get_at((x, bar.top))
        if not all(abs(pixel[i] - palette.panel_edge[i]) < 30 for i in range(3)):
            mismatches += 1
    assert mismatches == 0, f'{theme}: рамка перекрыта заливкой в {mismatches} точках'


def test_minimap_has_expected_geometry(app):
    scene = _scene(app)
    bar = _bar(scene)
    assert bar.height == MINIMAP_H
    assert bar.width > 200


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_minimap_colors_are_distinct(app, theme):
    """Сегменты игрока и ИИ должны заметно отличаться и быть насыщенными."""
    app.ctx.set_theme(theme)
    palette = app.ctx.palette

    def distance(a, b):
        return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5

    assert distance(palette.player_bright, palette.ai_bright) > 120
    assert distance(palette.player_bright, palette.panel) > 90
    assert distance(palette.ai_bright, palette.panel) > 90


def test_minimap_has_no_rounded_artifacts(app):
    """Регрессия: индикатор окна давал «зелёный полукруг» посреди полосы.

    Раньше окно рисовалось скруглённым контуром, который обрезался по
    внутренней области — оставались только боковые дуги. Теперь это тонкие
    вертикальные метки: акцентных пикселей должно быть мало и они должны
    стоять ровными столбцами.
    """
    scene = _scene(app)
    scene.draw(app.screen)

    bar = _bar(scene)
    palette = scene.ctx.palette
    accent = palette.accent

    def is_accent(pixel) -> bool:
        return all(abs(pixel[i] - accent[i]) < 30 for i in range(3))

    band = pg.Rect(bar.left + 50, bar.top + 4, bar.width - 100, bar.height - 8)
    columns: dict[int, int] = {}
    for y in range(band.top, band.bottom):
        for x in range(band.left, band.right):
            if is_accent(app.screen.get_at((x, y))):
                columns[x] = columns.get(x, 0) + 1

    # Метки тонкие: не больше 2-3 столбцов на каждую границу окна.
    assert len(columns) <= 8, f'слишком широкое пятно акцента: {len(columns)} столбцов'
    # И каждый столбец почти на всю высоту — то есть это ровная линия,
    # а не дуга.
    tall = [count for count in columns.values() if count >= band.height - 4]
    assert tall, f'метки не похожи на ровные линии: {sorted(columns.values())}'


def test_minimap_fill_has_segment_separators(app):
    """Между костями есть разделители — полоска читается как цепочка."""
    scene = _scene(app)
    scene.draw(app.screen)

    bar = _bar(scene)
    palette = scene.ctx.palette
    inner_top, inner_bottom = bar.top + 6, bar.bottom - 6

    def is_fill(pixel) -> bool:
        colors = {palette.player_bright, palette.ai_bright, palette.neutral_bright}
        return any(
            all(abs(pixel[i] - color[i]) < 40 for i in range(3))
            for color in colors
        )

    # Считаем «разрывы» заливки по центральной строке.
    row = (inner_top + inner_bottom) // 2
    gaps = 0
    previous = True
    for x in range(bar.left + 20, bar.right - 20):
        filled = is_fill(app.screen.get_at((x, row)))
        if previous and not filled:
            gaps += 1
        previous = filled

    assert gaps >= 3, f'разделителей слишком мало: {gaps}'

