"""Тесты обратной стороны кости: узор должен быть симметричен и отцентрирован."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.assets import Assets  # noqa: E402
from domino.ui.theme import THEME_ORDER, get_theme  # noqa: E402
from domino.ui.tiles import SKIN_ORDER, SKINS  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    pg.display.set_mode((10, 10))
    yield
    pg.quit()


def _diamond_bbox(sprite, color) -> pg.Rect:
    """Границы ромба внутри лица, без рамки и центральной линии."""
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


def _pattern_mask(sprite, color) -> pg.Mask:
    """Маска пикселей узора рубашки."""
    surface = sprite.surface
    pad = sprite.pad
    layer = pg.Surface((sprite.width, sprite.height), pg.SRCALPHA)
    for y in range(sprite.height):
        for x in range(sprite.width):
            pixel = surface.get_at((pad + x, pad + y))
            if all(abs(pixel[i] - color[i]) < 26 for i in range(3)) and pixel.a > 120:
                layer.set_at((x, y), (255, 255, 255, 255))
    return pg.mask.from_surface(layer)


@pytest.mark.parametrize('theme', THEME_ORDER)
@pytest.mark.parametrize('cell', [34, 56, 60])
def test_diamond_is_centered(app, theme, cell):
    """Регрессия: ромб был смещён на 1 px из-за draw.polygon с толщиной."""
    skin = SKINS['bone']
    sprite = Assets(get_theme(theme), (10, 10), skin).tile_back(cell, True)

    bbox = _diamond_bbox(sprite, skin.back_pattern)
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
    skin = SKINS['bone']
    sprite = Assets(get_theme('flat_dark'), (10, 10), skin).tile_back(cell, True)
    bbox = _diamond_bbox(sprite, skin.back_pattern)

    face_center_x = sprite.pad + sprite.width / 2
    face_center_y = sprite.pad + sprite.height / 2
    assert abs(bbox.centerx - face_center_x) <= 1
    assert abs(bbox.centery - face_center_y) <= 1


def test_diamond_horizontal_line_is_centered(app):
    """Разделительная линия идёт ровно по центру кости (набор «Кость»)."""
    skin = SKINS['bone']
    for cell in (34, 56, 60):
        sprite = Assets(get_theme('flat_dark'), (10, 10), skin).tile_back(cell, True)
        surface = sprite.surface

        # Берём участок справа от ромба, но внутри лица — там только линия.
        x = sprite.pad + sprite.width - 8
        rows = []
        for y in range(sprite.pad + 6, sprite.pad + sprite.height - 6):
            pixel = surface.get_at((x, y))
            if all(abs(pixel[i] - skin.back_pattern[i]) < 14 for i in range(3)):
                rows.append(y)

        assert rows, f'cell={cell}: линия не найдена'
        line_center = (min(rows) + max(rows)) / 2
        face_center = sprite.pad + sprite.height / 2
        assert abs(line_center - face_center) <= 1, (
            f'cell={cell}: линия на {line_center}, центр {face_center}'
        )


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
@pytest.mark.parametrize('cell', [34, 56, 60])
def test_back_pattern_is_centered_in_every_skin(app, skin_key, cell):
    """Узор любой рубашки отцентрирован по обеим осям лица."""
    skin = SKINS[skin_key]
    sprite = Assets(get_theme('flat_dark'), (10, 10), skin).tile_back(cell, True)
    mask = _pattern_mask(sprite, skin.back_pattern)
    bbox = mask.get_bounding_rects()[0].unionall(mask.get_bounding_rects()[1:])

    assert abs(bbox.centerx - sprite.width / 2) <= 1.5, (
        f'{skin_key}/{cell}: узор смещён по X на {bbox.centerx - sprite.width / 2}'
    )
    assert abs(bbox.centery - sprite.height / 2) <= 1.5, (
        f'{skin_key}/{cell}: узор смещён по Y на {bbox.centery - sprite.height / 2}'
    )


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_back_pattern_is_visible(app, skin_key):
    """Узор рубашки заметен, а не пара пикселей."""
    skin = SKINS[skin_key]
    sprite = Assets(get_theme('flat_dark'), (10, 10), skin).tile_back(56, True)
    mask = _pattern_mask(sprite, skin.back_pattern)
    # Даже у рамки и сетки узор занимает десятки пикселей.
    assert mask.count() > 60, f'{skin_key}: узор почти не виден ({mask.count()} px)'


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_back_of_horizontal_tile_works(app, skin_key):
    """Горизонтальная рубашка (2×1) тоже рисуется и центрируется."""
    skin = SKINS[skin_key]
    sprite = Assets(get_theme('flat_dark'), (10, 10), skin).tile_back(56, vertical=False)
    assert sprite.width == 112 and sprite.height == 56
    mask = _pattern_mask(sprite, skin.back_pattern)
    rects = mask.get_bounding_rects()
    bbox = rects[0].unionall(rects[1:])
    assert abs(bbox.centerx - sprite.width / 2) <= 1.5
