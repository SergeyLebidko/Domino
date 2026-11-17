"""Тесты воспроизводимости снимков документации."""

from __future__ import annotations

import hashlib
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _digest(surface: pg.Surface) -> str:
    return hashlib.md5(pg.image.tobytes(surface, 'RGB')).hexdigest()


def test_game_scene_accepts_seed(app):
    """Сцена должна принимать сид: иначе снимки каждый раз разные."""
    first = GameScene(app, seed=12)
    second = GameScene(app, seed=12)
    assert first.session.state.hands == second.session.state.hands
    assert first.session.state.chain == second.session.state.chain


def test_different_seeds_give_different_deals(app):
    """Сид действительно влияет на раздачу, а не игнорируется."""
    deals = {
        GameScene(app, seed=seed).session.state.hands
        for seed in (1, 2, 3, 4, 5)
    }
    assert len(deals) == 5, 'разные сиды дают одинаковые раздачи'


def test_scene_with_seed_draws_identically(app):
    """Регрессия: снимки game.png менялись от прогона к прогону.

    GameScene сеял random.randrange() без сида, поэтому каждая отрисовка
    давала новую раздачу и файл скриншота «дрожал» в git.
    """
    first = GameScene(app, seed=12)
    first.session.enable_ai = False
    first.update(0.016)
    first.draw(app.screen)
    one = _digest(app.screen.copy())

    second = GameScene(app, seed=12)
    second.session.enable_ai = False
    second.update(0.016)
    second.draw(app.screen)
    two = _digest(app.screen.copy())

    assert one == two, 'сцена с одним сидом рисуется по-разному'


def test_docs_screenshots_are_reproducible(app, tmp_path):
    """Два прогона tools.docs должны давать побайтово одинаковые снимки."""
    from tools.screens import render_game

    first = tmp_path / 'first.png'
    second = tmp_path / 'second.png'
    render_game('flat_dark', str(first))
    render_game('flat_dark', str(second))

    assert first.read_bytes() == second.read_bytes(), (
        'снимок игры не воспроизводится: git будет видеть ложные изменения'
    )
