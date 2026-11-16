"""Тесты обратной стороны кости: ромб должен быть отцентрирован."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.assets import Assets  # noqa: E402
from domino.ui.theme import THEME_ORDER, get_theme  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    pg.display.set_mode((10, 10))
    yield
    pg.quit()


def _pattern_bbox(sprite, color) -> pg.Rect:
    """Границы узора внутри лица, без рамки и центральной линии."""
    surface = sprite.surface
    pad = sprite.pad
    face = pg.Rect(pad, pad, sprite.width, sprite.height)
    inner = face.inflate(-14, -14)

    left = top = None
    right = bottom = None
    for y in range(inner.top, inner.bottom):
        for x in range(inner.left, inner.right):
            pixel = surface.get_at((x, y))
            if not all(abs(pixel[i] - color[i]) < 14 for i in range(3)):
                continue
            left = x if left is None else min(left, x)
            right = x if right is None else max(right, x)
            top = y if top is None else min(top, y)
            bottom = y if bottom is None else max(bottom, y)

    assert left is not None, 'узор не найден'
    return pg.Rect(left, top, right - left + 1, bottom - top + 1)


@pytest.mark.parametrize('theme', THEME_ORDER)
@pytest.mark.parametrize('cell', [34, 56, 60])
def test_diamond_is_centered(app, theme, cell):
    """Регрессия: ромб был смещён на 1 px из-за draw.polygon с толщиной."""
    palette = get_theme(theme)
    sprite = Assets(palette, (10, 10)).tile_back(cell, True)

    bbox = _pattern_bbox(sprite, palette.tile_back_pattern)
    face_center_x = sprite.pad + sprite.width / 2
    face_center_y = sprite.pad + sprite.height / 2

    assert abs(bbox.centerx - face_center_x) <= 0.5, (
        f'{theme}/{cell}: ромб смещён по X на {bbox.centerx - face_center_x}'
    )
    assert abs(bbox.centery - face_center_y) <= 0.5, (
        f'{theme}/{cell}: ромб смещён по Y на {bbox.centery - face_center_y}'
    )


@pytest.mark.parametrize('cell', [34, 56, 60])
def test_diamond_center_matches_face_center(app, cell):
    """Центр ромба совпадает с центром лица по обеим осям."""
    palette = get_theme('flat_dark')
    sprite = Assets(palette, (10, 10)).tile_back(cell, True)
    bbox = _pattern_bbox(sprite, palette.tile_back_pattern)

    face_center_x = sprite.pad + sprite.width / 2
    face_center_y = sprite.pad + sprite.height / 2
    assert abs(bbox.centerx - face_center_x) <= 1
    assert abs(bbox.centery - face_center_y) <= 1


def test_horizontal_line_is_centered(app):
    """Разделительная линия идёт ровно по центру кости."""
    palette = get_theme('flat_dark')
    for cell in (34, 56, 60):
        sprite = Assets(palette, (10, 10)).tile_back(cell, True)
        surface = sprite.surface

        # Берём участок справа от ромба, но внутри лица — там только линия.
        x = sprite.pad + sprite.width - 8
        rows = []
        for y in range(sprite.pad + 6, sprite.pad + sprite.height - 6):
            pixel = surface.get_at((x, y))
            if all(abs(pixel[i] - palette.tile_back_pattern[i]) < 14 for i in range(3)):
                rows.append(y)

        assert rows, f'cell={cell}: линия не найдена'
        line_center = (min(rows) + max(rows)) / 2
        face_center = sprite.pad + sprite.height / 2
        assert abs(line_center - face_center) <= 1, (
            f'cell={cell}: линия на {line_center}, центр {face_center}'
        )


def test_back_of_horizontal_tile_works(app):
    """Горизонтальная рубашка (2×1) тоже рисуется и центрируется."""
    palette = get_theme('flat_dark')
    sprite = Assets(palette, (10, 10)).tile_back(56, vertical=False)
    assert sprite.width == 112 and sprite.height == 56
    bbox = _pattern_bbox(sprite, palette.tile_back_pattern)
    assert abs(bbox.centerx - (sprite.pad + sprite.width / 2)) <= 0.5
