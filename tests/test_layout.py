"""Тесты раскладки экрана: панели не должны слипаться."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino import settings  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402
from domino.ui.theme import THEME_ORDER  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def test_board_and_hand_are_separated(app):
    """Регрессия: поле и панель руки стояли вплотную друг к другу."""
    scene = GameScene(app)
    gap = scene.hand_rect.top - scene.board_rect.bottom
    assert gap == settings.BOARD_MARGIN, f'зазор {gap} вместо {settings.BOARD_MARGIN}'


def test_board_and_sidebar_are_separated(app):
    """Регрессия: после правки раскладки поле прилипло к правой панели."""
    scene = GameScene(app)
    gap = scene.sidebar_rect.left - scene.board_rect.right
    assert gap == settings.BOARD_MARGIN, f'зазор {gap} вместо {settings.BOARD_MARGIN}'


def test_hand_and_sidebar_are_separated(app):
    """Панель руки тоже не должна касаться правой панели."""
    scene = GameScene(app)
    gap = scene.sidebar_rect.left - scene.hand_rect.right
    assert gap == settings.BOARD_MARGIN, f'зазор {gap} вместо {settings.BOARD_MARGIN}'


def test_all_gaps_are_equal(app):
    """Все зазоры между областями и краями одинаковы."""
    scene = GameScene(app)
    margin = settings.BOARD_MARGIN
    gaps = {
        'левый край': scene.board_rect.left,
        'правый край': settings.W - scene.sidebar_rect.right,
        'верх': scene.board_rect.top - settings.TOPBAR_H,
        'низ': settings.H - scene.hand_rect.bottom,
        'поле/рука': scene.hand_rect.top - scene.board_rect.bottom,
        'поле/сайдбар': scene.sidebar_rect.left - scene.board_rect.right,
        'рука/сайдбар': scene.sidebar_rect.left - scene.hand_rect.right,
    }
    for name, gap in gaps.items():
        assert gap == margin, f'{name}: {gap} вместо {margin}'


def test_margins_are_symmetric(app):
    """Отступы от краёв окна одинаковы со всех сторон."""
    scene = GameScene(app)
    margin = settings.BOARD_MARGIN
    content_top = settings.TOPBAR_H + margin

    assert scene.board_rect.left == margin
    assert scene.board_rect.top == content_top
    assert settings.W - scene.sidebar_rect.right == margin
    assert settings.H - scene.hand_rect.bottom == margin


def test_sidebar_matches_content_height(app):
    """Сайдбар по высоте равен полю + зазор + панель руки."""
    scene = GameScene(app)
    total = scene.board_rect.height + settings.BOARD_MARGIN + scene.hand_rect.height
    assert scene.sidebar_rect.height == total
    assert scene.sidebar_rect.top == scene.board_rect.top


def test_board_and_hand_have_equal_width(app):
    """Поле и рука выровнены по ширине и левому краю."""
    scene = GameScene(app)
    assert scene.board_rect.width == scene.hand_rect.width
    assert scene.board_rect.left == scene.hand_rect.left


def test_panels_do_not_overlap(app):
    """Никакие две панели не пересекаются."""
    scene = GameScene(app)
    panels = {
        'board': scene.board_rect,
        'hand': scene.hand_rect,
        'sidebar': scene.sidebar_rect,
    }
    names = list(panels)
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            assert not panels[first].colliderect(panels[second]), (
                f'{first} и {second} пересекаются'
            )


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_gap_is_visible_in_render(app, theme):
    """Между панелями должен быть виден фон, а не сплошная заливка."""
    app.ctx.set_theme(theme)
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(app.screen)

    palette = app.ctx.palette
    gap_top = scene.board_rect.bottom + 2
    gap_bottom = scene.hand_rect.top - 2
    x = scene.board_rect.centerx

    def near(pixel, color) -> bool:
        return all(abs(pixel[i] - color[i]) < 6 for i in range(3))

    for y in range(gap_top, gap_bottom):
        pixel = app.screen.get_at((x, y))[:3]
        assert not near(pixel, palette.board), f'{theme}: в зазоре цвет поля'
        assert not near(pixel, palette.panel), f'{theme}: в зазоре цвет панели'


def test_hand_tiles_fit_inside_panel(app):
    """Кости не выходят за панель руки после изменения высоты."""
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.update(0.016)

    for tile in scene.hand.tiles:
        rect = tile.rect.move(0, -int(tile.lift))
        assert scene.hand_rect.contains(rect), f'кость {tile.index} выходит за панель'
