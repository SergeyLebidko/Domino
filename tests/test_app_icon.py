"""Тесты иконки приложения: костяшка 1:1."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.app import render_app_icon  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    pg.display.set_mode((10, 10))
    yield
    pg.quit()


def _face_rect(icon: pg.Surface) -> pg.Rect:
    """Границы светлого лица кости (без прозрачных полей)."""
    mask = pg.mask.from_surface(icon)
    rects = mask.get_bounding_rects()
    assert rects, 'иконка пустая'
    return rects[0].unionall(rects[1:])


def _pips(icon: pg.Surface) -> list[pg.Rect]:
    """Тёмные точки внутри лица."""
    face = _face_rect(icon)
    dark = pg.Surface(icon.get_size(), pg.SRCALPHA)
    for y in range(face.top, face.bottom):
        for x in range(face.left, face.right):
            pixel = icon.get_at((x, y))
            if pixel.a < 200:
                continue
            if pixel[0] < 110 and pixel[1] < 120 and pixel[2] < 130:
                dark.set_at((x, y), (255, 255, 255, 255))
    # Отсекаем разделитель: он тонкий и идёт по всей ширине.
    return [r for r in pg.mask.from_surface(dark).get_bounding_rects()
            if r.width >= 2 and r.height >= 2 and r.width > r.height * 0.5]


@pytest.mark.parametrize('size', [16, 24, 32, 48, 64])
def test_icon_has_exact_size(app, size):
    """Windows и Linux просят разные размеры — любой должен отдаваться."""
    icon = render_app_icon(size)
    assert icon.get_size() == (size, size)


def test_icon_is_a_vertical_tile(app):
    """Регрессия: иконка была почти квадратной, а костяшка 1:1 — вытянутая."""
    icon = render_app_icon(64)
    face = _face_rect(icon)
    ratio = face.height / face.width
    assert 1.3 <= ratio <= 1.75, f'соотношение сторон лица {ratio:.2f}, а не 2:1'


def test_icon_has_exactly_two_pips(app):
    """Костяшка 1:1 — по одной точке в каждой половинке."""
    icon = render_app_icon(64)
    pips = _pips(icon)
    assert len(pips) == 2, f'точек {len(pips)}, а должно быть 2'


def test_pips_are_stacked_vertically(app):
    """Точки стоят одна над другой по центру — это кость 1:1, а не 2:2."""
    icon = render_app_icon(64)
    pips = sorted(_pips(icon), key=lambda r: r.centery)
    assert len(pips) == 2

    face = _face_rect(icon)
    top, bottom = pips
    # Одна выше центра, другая ниже.
    assert top.centery < face.centery < bottom.centery
    # Обе по вертикальной оси кости.
    assert abs(top.centerx - bottom.centerx) <= 2
    assert abs(top.centerx - face.centerx) <= 2


def test_pips_do_not_touch_the_divider(app):
    """Точки не должны сливаться с разделительной линией."""
    icon = render_app_icon(64)
    pips = _pips(icon)
    face = _face_rect(icon)
    for pip in pips:
        distance = abs(pip.centery - face.centery)
        assert distance > pip.height, (
            f'точка в {distance} px от центра при высоте {pip.height}'
        )


def test_icon_has_transparent_corners(app):
    """Углы прозрачные — иначе в трее иконка выглядит квадратом."""
    icon = render_app_icon(64)
    for pos in ((0, 0), (63, 0), (0, 63), (63, 63)):
        assert icon.get_at(pos).a < 40, f'угол {pos} не прозрачный'


def test_icon_is_visible_at_small_size(app):
    """На 16 px иконка не должна выродиться в пустой квадрат."""
    icon = render_app_icon(16)
    mask = pg.mask.from_surface(icon)
    assert mask.count() > 40, f'всего {mask.count()} видимых пикселей'


def test_icon_has_light_face(app):
    """Лицо светлое: тёмная иконка теряется в тёмной теме рабочего стола."""
    icon = render_app_icon(64)
    face = _face_rect(icon)
    pixel = icon.get_at(face.center)
    assert pixel.a > 200
    brightness = 0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2]
    assert brightness > 170, f'лицо слишком тёмное ({brightness:.0f})'
