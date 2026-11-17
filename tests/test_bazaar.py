"""Тесты панели «базар»: воздух вокруг кости и отступ от шапки."""

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


def _tile_box(scene, app) -> tuple[int, int, int]:
    """Прямоугольник, который занимает кость базара вместе с тенью."""
    rect = scene._bazaar_visual()
    sprite = app.ctx.assets.tile_back(settings.CELL_BAZAAR_TILE, True)
    top = rect.centery - sprite.height // 2
    return (top - sprite.pad, top + sprite.height + sprite.pad, sprite.height)


def test_bazaar_panel_is_tall_enough_for_the_tile(app):
    """Регрессия: кость стояла в 3 px от края и выглядела прижатой."""
    scene = GameScene(app)
    rect = scene._bazaar_visual()
    sprite = app.ctx.assets.tile_back(settings.CELL_BAZAAR_TILE, True)

    padding = (rect.height - sprite.height) / 2
    assert padding >= 8, (
        f'воздух вокруг кости {padding} px — нужно не меньше 8'
    )


def test_bazaar_tile_has_equal_padding(app):
    """Сверху и снизу воздух одинаковый, иначе кость «съезжает»."""
    scene = GameScene(app)
    rect = scene._bazaar_visual()
    sprite = app.ctx.assets.tile_back(settings.CELL_BAZAAR_TILE, True)

    top = rect.centery - sprite.height // 2
    above = top - rect.top
    below = rect.bottom - (top + sprite.height)
    assert abs(above - below) <= 1, f'сверху {above}, снизу {below}'


def test_bazaar_tile_stays_inside_the_panel(app):
    """Вместе с тенью кость не должна вылезать за границы панели."""
    scene = GameScene(app)
    rect = scene._bazaar_visual()
    top, bottom, _ = _tile_box(scene, app)

    assert top >= rect.top - 1, f'тень кости вылезает сверху на {rect.top - top}'
    assert bottom <= rect.bottom + 1, (
        f'тень кости вылезает снизу на {bottom - rect.bottom}'
    )


def test_bazaar_does_not_stick_to_topbar(app):
    """Регрессия: панель базара прилипала к шапке (зазор 6 px)."""
    scene = GameScene(app)
    rect = scene._bazaar_visual()
    gap = rect.top - scene.topbar.bottom
    assert gap >= 8, f'зазор до шапки {gap} px'


def test_bazaar_does_not_cover_thinking_indicator(app):
    """Базар не перекрывает индикатор хода в шапке."""
    scene = GameScene(app)
    rect = scene._bazaar_visual()
    assert rect.top >= scene.topbar.bottom


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_bazaar_sits_on_board_edge(app, theme):
    """Базар висит на верхней кромке поля, выступая за неё вверх.

    Так задумано: панель перекрывает рамку поля сверху и читается как
    ярлык на ней. Важно, чтобы она не уезжала вбок за край поля.
    """
    fresh = App(theme=theme, headless=True)
    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False
    rect = scene._bazaar_visual()
    board = scene.board_rect

    assert rect.left >= board.left, f'{theme}: базар левее поля'
    assert rect.right <= board.right, f'{theme}: базар правее поля'
    assert board.right - rect.right >= 10, f'{theme}: базар прилип к краю поля'
    # Верхняя часть панели выступает над полем — это ожидаемая «нашлёпка».
    assert rect.top < board.top


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_bazaar_draws_without_error(app, theme):
    """Отрисовка базара не падает ни в одной теме."""
    fresh = App(theme=theme, headless=True)
    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(fresh.screen)
    assert scene.session.tile_count_ok


def test_click_on_bazaar_takes_a_tile(app):
    """Клик по панели базара берёт кость — попадание считается по ней.

    Добор доступен только когда ходов нет, поэтому состояние подгоняем:
    рука из костей, которые не подходят к концам цепочки.
    """
    from dataclasses import replace

    from domino.engine import make_tile

    fresh = App(headless=True)
    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False

    state = scene.session.state
    dead = tuple(make_tile(a, a) for a in (0, 0, 0, 1, 1, 2, 2))
    left, right = state.left_end, state.right_end
    hand = tuple(t for t in dead if not (t.has(left) or t.has(right)))
    if not hand:
        pytest.skip('не удалось собрать руку без ходов')
    scene.session.state = replace(state, hands=(hand, state.hands[1]), turn=0)
    scene._sync()

    before = scene.session.state.bazaar_count
    assert before > 0
    assert not scene.session.can_move(0), 'предпосылка теста неверна'

    center = scene._bazaar_visual().center
    scene.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=center, button=pg.BUTTON_LEFT))
    # По правилам добор идёт до первой играбельной кости, поэтому из базара
    # уходит одна или несколько костей.
    assert scene.session.state.bazaar_count < before, 'клик по базару ничего не взял'
    assert len(scene.session.state.hands[0]) > len(hand)


def test_bazaar_panel_size_comes_from_settings(app):
    """Размеры панели заданы в настройках, а не магическими числами."""
    assert settings.BAZAAR_W > 0
    assert settings.BAZAAR_H > 0
    assert settings.BAZAAR_GAP > 0
    scene = GameScene(app)
    rect = scene._bazaar_visual()
    assert (rect.width, rect.height) == (settings.BAZAAR_W, settings.BAZAAR_H)
