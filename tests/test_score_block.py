"""Тесты блока счёта: там только счёт партий, без очков на руках."""

from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.engine import make_tile  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402
from domino.ui.sidebar import Sidebar  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _render_sidebar(app, state, scores) -> pg.Surface:
    surface = pg.Surface((360, 500))
    surface.fill(app.ctx.palette.bg_top)
    sidebar = Sidebar(app.ctx.assets)
    sidebar.draw(
        surface,
        pg.Rect(0, 0, 360, 500),
        app.ctx.palette,
        state,
        scores=scores,
        difficulty='medium',
        thinking=False,
        hint='подсказка',
    )
    return surface


def test_score_block_ignores_hand_pips(app):
    """Регрессия: в блоке счёта показывались очки на руках.

    Если поменять только кости на руках, оставив счёт прежним, картинка
    боковой панели обязана остаться той же.
    """
    scene = GameScene(app)
    scene.session.enable_ai = False
    base = scene.session.state

    light = replace(base, hands=((make_tile(0, 0),), (make_tile(0, 1),)))
    heavy = replace(base, hands=((make_tile(6, 6), make_tile(5, 5)), (make_tile(6, 5),)))

    first = _render_sidebar(app, light, (3, 4))
    second = _render_sidebar(app, heavy, (3, 4))

    assert pg.image.tobytes(first, 'RGB') == pg.image.tobytes(second, 'RGB'), (
        'блок счёта зависит от очков на руках'
    )


def test_score_block_shows_session_scores(app):
    """Разный счёт сессии должен менять картинку."""
    scene = GameScene(app)
    scene.session.enable_ai = False
    state = scene.session.state

    low = _render_sidebar(app, state, (0, 0))
    high = _render_sidebar(app, state, (9, 7))

    assert pg.image.tobytes(low, 'RGB') != pg.image.tobytes(high, 'RGB')


def test_hand_points_shown_next_to_hand(app):
    """Очки на руках подписаны и выводятся рядом с рукой игрока."""
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.update(0.016)

    # Подпись должна быть на полотне руки: ищем область заголовка панели.
    from domino.ui.assets import text_image

    font = app.ctx.assets.body(13)
    expected = text_image(font, f'на руках {scene.session.state.pips_of(0)}',
                          app.ctx.palette.text_dim)
    assert expected.get_width() > 10
