"""Тесты наборов оформления костей, независимых от темы стола."""

from __future__ import annotations

import math
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino import settings  # noqa: E402
from domino.config import Config  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.assets import Assets  # noqa: E402
from domino.ui.theme import THEME_ORDER, get_theme  # noqa: E402
from domino.ui.tiles import (  # noqa: E402
    BACK_STYLES,
    PIP_STYLES,
    SKIN_ORDER,
    SKINS,
    get_skin,
    next_skin,
)


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _luminance(color) -> float:
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]


def test_three_skins_are_defined(app):
    assert len(SKIN_ORDER) == 3
    assert set(SKIN_ORDER) == set(SKINS)
    for key in SKIN_ORDER:
        assert SKINS[key].key == key
        assert SKINS[key].title


def test_skin_styles_are_known(app):
    """Стили точек и рубашек должны быть реализованы в рендере."""
    for skin in SKINS.values():
        assert skin.pip_style in PIP_STYLES, skin.key
        assert skin.back_style in BACK_STYLES, skin.key


def test_every_skin_has_readable_contrast(app):
    """Регрессия: наборы отличались от темы, но не друг от друга по контрасту.

    Точки обязаны выделяться на лице кости, иначе кость «слепая».
    """
    for key in SKIN_ORDER:
        skin = SKINS[key]
        delta = abs(_luminance(skin.face) - _luminance(skin.pip))
        assert delta >= 90, f'{key}: контраст точек всего {delta:.0f}'


def test_skins_differ_from_each_other(app):
    """Наборы должны быть заметно разными, а не оттенками одного."""
    skins = [SKINS[key] for key in SKIN_ORDER]
    for index, first in enumerate(skins):
        for second in skins[index + 1:]:
            delta = math.dist(_luminance(first.face), _luminance(second.face)) if False else abs(
                _luminance(first.face) - _luminance(second.face)
            )
            assert delta >= 45, (
                f'{first.key} и {second.key}: лица почти одинаковы ({delta:.0f})'
            )


def test_skins_render_differently(app):
    """Картинки кости в разных наборах по-разному выглядят попиксельно."""
    theme = get_theme('flat_dark')
    images = {}
    for key in SKIN_ORDER:
        sprite = Assets(theme, (10, 10), SKINS[key]).tile(6, 4, True, 56)
        images[key] = pg.transform.smoothscale(sprite.surface, (28, 56))
        images[key] = images[key].copy()

    for index, first in enumerate(SKIN_ORDER):
        for second in SKIN_ORDER[index + 1:]:
            differing = 0
            one, two = images[first], images[second]
            for y in range(one.get_height()):
                for x in range(one.get_width()):
                    a, b = one.get_at((x, y)), two.get_at((x, y))
                    if any(abs(a[i] - b[i]) > 12 for i in range(3)):
                        differing += 1
            total = one.get_width() * one.get_height()
            share = differing / total
            assert share > 0.5, (
                f'{first} и {second}: отличаются только {share:.0%} пикселей'
            )


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
@pytest.mark.parametrize('cell', [34, 56, 60])
def test_skin_renders_at_every_size(app, skin_key, cell):
    """Каждый набор рисуется на всех размерах костей в обеих ориентациях."""
    theme = get_theme('flat_dark')
    assets = Assets(theme, (10, 10), SKINS[skin_key])
    for vertical in (True, False):
        face = assets.tile(6, 3, vertical, cell)
        back = assets.tile_back(cell, vertical)
        if vertical:
            assert (face.width, face.height) == (cell, 2 * cell)
            assert (back.width, back.height) == (cell, 2 * cell)
        else:
            assert (face.width, face.height) == (2 * cell, cell)
            assert (back.width, back.height) == (2 * cell, cell)


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
@pytest.mark.parametrize('cell', [34, 56, 60])
def test_tile_face_uses_skin_color(app, skin_key, cell):
    """Заливка лица берётся из набора, а не из темы стола."""
    skin = SKINS[skin_key]
    sprite = Assets(get_theme('flat_dark'), (10, 10), skin).tile(0, 0, True, cell)
    # Верхняя половинка пустая: в её центре только заливка лица.
    x = sprite.pad + sprite.width // 2
    y = sprite.pad + cell // 2
    pixel = sprite.surface.get_at((x, y))
    assert all(abs(pixel[i] - skin.face[i]) < 26 for i in range(3)), (
        f'{skin_key}: лицо {pixel[:3]} вместо {skin.face}'
    )


def test_skin_is_independent_of_theme(app):
    """Один набор в разных темах даёт одинаковые кости."""
    images = []
    for theme_key in THEME_ORDER:
        assets = Assets(get_theme(theme_key), (10, 10), SKINS['amber'])
        sprite = assets.tile(5, 2, True, 56)
        images.append(sprite.surface.copy())

    first = images[0]
    for other in images[1:]:
        for y in range(0, first.get_height(), 3):
            for x in range(0, first.get_width(), 3):
                a, b = first.get_at((x, y)), other.get_at((x, y))
                assert all(abs(a[i] - b[i]) <= 2 for i in range(3)), (
                    f'кость набора не зависит от темы: {a[:3]} != {b[:3]}'
                )


def test_set_skin_clears_cache(app):
    """Смена набора сбрасывает кэш костей."""
    assets = Assets(get_theme('flat_dark'), (10, 10), SKINS['bone'])
    before = assets.tile(6, 6, True, 56)
    assets.set_skin(SKINS['amber'])
    after = assets.tile(6, 6, True, 56)
    assert before is not after
    assert assets.skin.key == 'amber'


def test_get_skin_falls_back_to_default(app):
    assert get_skin('нет-такого').key == settings.DEFAULT_TILES
    assert get_skin('amber').key == 'amber'


def test_next_skin_cycles(app):
    seen = []
    key = SKIN_ORDER[0]
    for _ in range(len(SKIN_ORDER)):
        key = next_skin(key).key
        seen.append(key)
    assert seen[-1] == SKIN_ORDER[0]
    assert set(seen) == set(SKIN_ORDER)


def test_app_starts_with_default_skin(app):
    fresh = App(headless=True)
    assert fresh.ctx.tiles in SKIN_ORDER
    assert fresh.ctx.assets.skin.key == fresh.ctx.tiles


def test_context_set_tiles_changes_assets(app):
    fresh = App(headless=True)
    fresh.ctx.set_tiles('amber')
    assert fresh.ctx.tiles == 'amber'
    assert fresh.ctx.assets.skin.key == 'amber'


def test_context_cycle_tiles(app):
    fresh = App(headless=True, tiles='bone')
    fresh.ctx.cycle_tiles()
    assert fresh.ctx.tiles == 'graphite'
    fresh.ctx.cycle_tiles()
    assert fresh.ctx.tiles == 'amber'
    fresh.ctx.cycle_tiles()
    assert fresh.ctx.tiles == 'bone'


# -- конфиг ---------------------------------------------------------------


def test_config_saves_and_loads_tiles(tmp_path):
    path = tmp_path / 'settings.json'
    Config(theme='club_green', tiles='amber', difficulty='hard', first_player=1).save(path)

    loaded = Config.load(path)
    assert loaded.tiles == 'amber'
    assert loaded.theme == 'club_green'


def test_config_without_tiles_uses_default(tmp_path):
    """Старый settings.json без поля tiles читается нормально."""
    path = tmp_path / 'settings.json'
    path.write_text('{"theme": "club_green", "difficulty": "easy"}', encoding='utf-8')

    loaded = Config.load(path)
    assert loaded.tiles == settings.DEFAULT_TILES
    assert loaded.theme == 'club_green'


def test_config_ignores_unknown_tiles(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('{"tiles": "неон"}', encoding='utf-8')
    assert Config.load(path).tiles == settings.DEFAULT_TILES


def test_settings_keys_match_skins(app):
    """Список допустимых значений в настройках совпадает с реальными наборами."""
    assert set(settings.TILES_KEYS) == set(SKIN_ORDER)
