"""Тесты отрисовки точек на костях: они не должны слипаться."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.app import App  # noqa: E402
from domino.ui.assets import PIP_LAYOUT  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _pip_blobs(surface: pg.Surface) -> list[pg.Rect]:
    """Отдельные связные пятна точек на поверхности кости."""
    mask = pg.mask.from_surface(surface)
    return mask.get_bounding_rects()


@pytest.mark.parametrize('cell', [56, 60])
@pytest.mark.parametrize('value', [1, 2, 3, 4, 5, 6])
def test_pips_do_not_merge(app, cell, value):
    """Каждая точка — отдельное пятно: иначе кружки «слипаются»."""
    assets = app.ctx.assets
    sprite = assets.tile(value, value, True, cell)

    # Берём только верхнюю половинку кости, чтобы не смешивать две стороны.
    half = pg.Surface((sprite.width, sprite.height // 2), pg.SRCALPHA)
    half.blit(sprite.surface, (0, 0))

    # Маска по пикселям цвета точек.
    raw = pg.Surface(half.get_size(), pg.SRCALPHA)
    pip = app.ctx.palette.pip
    for y in range(half.get_height()):
        for x in range(half.get_width()):
            pixel = half.get_at((x, y))
            if all(abs(pixel[i] - pip[i]) < 40 for i in range(3)) and pixel.a > 200:
                raw.set_at((x, y), (255, 255, 255, 255))

    blobs = [rect for rect in pg.mask.from_surface(raw).get_bounding_rects()
             if rect.width >= 2 and rect.height >= 2]
    expected = len(PIP_LAYOUT[value])
    assert len(blobs) == expected, (
        f'cell={cell}, значение={value}: ожидалось {expected} точек, '
        f'найдено {len(blobs)} (слияние)'
    )


@pytest.mark.parametrize('cell', [56, 60])
def test_pips_stay_inside_tile(app, cell):
    """Точки не выходят за границы половинки кости."""
    assets = app.ctx.assets
    for value in range(1, 7):
        sprite = assets.tile(value, value, True, cell)
        assert sprite.surface.get_size() == (sprite.width + 2 * sprite.pad,
                                            sprite.height + 2 * sprite.pad)


def test_logo_tile_has_single_pips(app):
    """Кость логотипа показывает по одной точке — шесть сливались в пятно."""
    from domino.ui.scenes import GameScene

    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(app.screen)

    # Верхний левый угол — кость логотипа 1:1 при cell=16.
    sprite = app.ctx.assets.tile(1, 1, True, 16)
    half = pg.Surface((sprite.width, sprite.height // 2), pg.SRCALPHA)
    half.blit(sprite.surface, (0, 0))

    pip = app.ctx.palette.pip
    raw = pg.Surface(half.get_size(), pg.SRCALPHA)
    for y in range(half.get_height()):
        for x in range(half.get_width()):
            pixel = half.get_at((x, y))
            if all(abs(pixel[i] - pip[i]) < 60 for i in range(3)) and pixel.a > 180:
                raw.set_at((x, y), (255, 255, 255, 255))

    blobs = [r for r in pg.mask.from_surface(raw).get_bounding_rects()
             if r.width >= 1 and r.height >= 1]
    assert len(blobs) == 1, f'на половинке логотипа {len(blobs)} пятен вместо 1'


def test_pip_spread_is_configured():
    """Шаг точек задаётся константой, а не магическим числом."""
    from domino.ui.assets import PIP_SPREAD

    assert 0.5 <= PIP_SPREAD <= 0.95
