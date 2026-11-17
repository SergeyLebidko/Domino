"""Тесты кнопок с иконками: центрирование, подписи, назначение."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.app import App  # noqa: E402
from domino.ui.theme import THEMES  # noqa: E402
from domino.ui.widgets import Button, _draw_icon, _icon_size  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _icon_bbox(surface: pg.Surface) -> pg.Rect | None:
    """Объединённые границы глифа (у паузы и меню несколько фигур)."""
    mask = pg.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    bbox = rects[0].unionall(rects[1:])
    return bbox


@pytest.mark.parametrize('name', ['tiles', 'palette', 'restart', 'pause', 'menu', 'close'])
def test_icon_is_centered(app, name):
    """Глиф обязан быть визуально отцентрирован в кнопке."""
    rect = pg.Rect(0, 0, 40, 40)
    surface = pg.Surface(rect.size, pg.SRCALPHA)
    _draw_icon(surface, name, rect.center, _icon_size(rect), (255, 255, 255))

    bbox = _icon_bbox(surface)
    assert bbox is not None, f'иконка {name} не нарисовалась'

    # Центр глифа совпадает с центром кнопки с точностью до 1,5 px.
    dx = abs(bbox.centerx - rect.centerx)
    dy = abs(bbox.centery - rect.centery)
    assert dx <= 1.5, f'{name}: смещение по X {dx}'
    assert dy <= 1.5, f'{name}: смещение по Y {dy}'


@pytest.mark.parametrize('name', ['tiles', 'palette', 'restart', 'pause'])
def test_icon_fits_inside_button(app, name):
    """Глиф не выходит за границы кнопки."""
    rect = pg.Rect(0, 0, 40, 40)
    surface = pg.Surface(rect.size, pg.SRCALPHA)
    _draw_icon(surface, name, rect.center, _icon_size(rect), (255, 255, 255))
    bbox = _icon_bbox(surface)
    assert rect.contains(bbox), f'{name}: {bbox} выходит за {rect}'


@pytest.mark.parametrize('name', ['tiles', 'palette', 'restart', 'pause'])
def test_icon_has_visible_pixels(app, name):
    """Глиф должен быть заметным, а не парой случайных пикселей."""
    rect = pg.Rect(0, 0, 40, 40)
    surface = pg.Surface(rect.size, pg.SRCALPHA)
    _draw_icon(surface, name, rect.center, _icon_size(rect), (255, 255, 255))
    mask = pg.mask.from_surface(surface)
    assert mask.count() > 40, f'{name}: слишком мало пикселей ({mask.count()})'


def test_topbar_buttons_have_text_labels(app):
    """У кнопок верхней панели должна быть подпись, а не только иконка."""
    from domino.ui.scenes import GameScene

    scene = GameScene(app)
    labels = {button.icon: button.label for button in scene.buttons}
    assert set(labels) == {'tiles', 'palette', 'restart', 'pause'}
    for icon, label in labels.items():
        assert label, f'кнопка {icon} без подписи'


def test_topbar_buttons_do_not_overlap(app):
    """Кнопки верхней панели не перекрывают друг друга и не выходят за окно."""
    from domino import settings
    from domino.ui.scenes import GameScene

    scene = GameScene(app)
    buttons = scene.buttons
    for index, first in enumerate(buttons):
        assert settings.W - settings.BOARD_MARGIN >= first.rect.right
        assert first.rect.left >= 0
        for second in buttons[index + 1:]:
            assert not first.rect.colliderect(second.rect), (
                f'{first.icon} и {second.icon} перекрываются'
            )


def test_theme_button_cycles_theme_and_updates_label(app):
    from domino.ui.scenes import GameScene

    app.ctx.set_theme('flat_dark')
    scene = GameScene(app)
    scene.update(0.016)

    before = app.ctx.theme
    button = scene.btn_theme
    scene.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=button.rect.center))
    scene.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=button.rect.center))

    assert app.ctx.theme != before
    assert scene.btn_theme.label == THEMES[app.ctx.theme].title


def test_buttons_render_in_every_theme(app):
    from domino.ui.scenes import GameScene

    for key in THEMES:
        app.ctx.set_theme(key)
        scene = GameScene(app)
        scene.session.enable_ai = False
        scene.update(0.016)
        scene.draw(app.screen)
        for button in scene.buttons:
            button.draw(app.screen, app.ctx.assets, app.ctx.palette)


def test_button_with_icon_and_label_centers_group(app):
    """Иконка + подпись центрируются как единая группа."""
    rect = pg.Rect(0, 0, 140, 36)
    theme = app.ctx.palette
    assets = app.ctx.assets

    filled = pg.Surface(rect.size, pg.SRCALPHA)
    Button(pg.Rect(rect), 'Тема', icon='palette').draw(filled, assets, theme)

    # Та же кнопка без содержимого — чтобы отделить фон и рамку.
    plain = pg.Surface(rect.size, pg.SRCALPHA)
    Button(pg.Rect(rect), '').draw(plain, assets, theme)

    bbox = None
    for y in range(rect.height):
        for x in range(rect.width):
            if filled.get_at((x, y)) == plain.get_at((x, y)):
                continue
            pixel = pg.Rect(x, y, 1, 1)
            bbox = pixel if bbox is None else bbox.union(pixel)

    assert bbox is not None, 'на кнопке ничего не нарисовано'
    # Содержимое не прилипает к краям и симметрично относительно центра.
    assert bbox.left >= 6, bbox
    assert rect.right - bbox.right >= 6, bbox
    assert abs(bbox.centerx - rect.centerx) <= 3, bbox
