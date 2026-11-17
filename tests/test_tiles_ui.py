"""Тесты выбора костей в интерфейсе: меню, пауза, верхняя панель."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene, MenuScene, PauseScene  # noqa: E402
from domino.ui.tiles import SKIN_ORDER, SKINS  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _click(button) -> None:
    """Полный клик по кнопке Button."""
    center = button.rect.center
    button.handle(pg.event.Event(pg.MOUSEMOTION, pos=center, rel=(0, 0), buttons=(0, 0, 0)))
    button.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=center, button=pg.BUTTON_LEFT))
    button.handle(pg.event.Event(pg.MOUSEBUTTONUP, pos=center, button=pg.BUTTON_LEFT))


def _click_segment(scene, segment, index: int) -> None:
    """Клик по сегменту через обработчик сцены — проверяем подключение."""
    center = segment.option_rect(index).center
    scene.handle(pg.event.Event(pg.MOUSEMOTION, pos=center, rel=(0, 0), buttons=(0, 0, 0)))
    scene.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=center, button=pg.BUTTON_LEFT))
    scene.handle(pg.event.Event(pg.MOUSEBUTTONUP, pos=center, button=pg.BUTTON_LEFT))


# -- меню -----------------------------------------------------------------


def test_menu_has_tiles_selector(app):
    scene = MenuScene(app)
    options = [key for key, _ in scene.tiles_select.options]
    assert options == list(SKIN_ORDER)


def test_menu_selectors_do_not_overlap(app):
    """Пять тем не влезают в половину строки — выборы идут друг под другом."""
    scene = MenuScene(app)
    rows = [scene.theme_select.rect, scene.tiles_select.rect, scene.first_select.rect]
    for index, first in enumerate(rows):
        for second in rows[index + 1:]:
            assert not first.colliderect(second), 'ряды выбора наезжают друг на друга'

    # Все три идут сверху вниз в порядке отрисовки.
    assert scene.theme_select.rect.bottom <= scene.tiles_select.rect.top
    assert scene.tiles_select.rect.bottom <= scene.first_select.rect.top


def test_menu_click_changes_skin(app):
    scene = MenuScene(app)
    app.ctx.set_tiles('bone')

    _click_segment(scene, scene.tiles_select, SKIN_ORDER.index('amber'))

    assert app.ctx.tiles == 'amber'
    assert app.ctx.assets.skin.key == 'amber'
    app.ctx.set_tiles('bone')


def test_menu_click_does_not_change_theme(app):
    """Выбор костей не должен заодно переключать тему стола."""
    scene = MenuScene(app)
    app.ctx.set_tiles('bone')
    theme_before = app.ctx.theme

    _click_segment(scene, scene.tiles_select, SKIN_ORDER.index('graphite'))

    assert app.ctx.theme == theme_before
    app.ctx.set_tiles('bone')


def test_menu_option_labels_fit_their_segments(app):
    """Регрессия: «Классика» (92 px) не влезала в сегмент шириной 83 px."""
    scene = MenuScene(app)
    assets = app.ctx.assets
    font = assets.body(17, bold=True)

    for selector, name in ((scene.theme_select, 'тема'), (scene.tiles_select, 'кости')):
        for index, (key, label) in enumerate(selector.options):
            rect = selector.option_rect(index).inflate(-4, -4)
            width = font.size(label)[0]
            assert width <= rect.width - 4, (
                f'{name}/{key}: подпись «{label}» {width} px не влезает в '
                f'сегмент {rect.width} px'
            )


def test_menu_shows_current_skin(app):
    fresh = App(headless=True, tiles='amber')
    scene = MenuScene(fresh)
    assert scene.tiles_select.selected == 'amber'
    assert [key for key, _ in scene.tiles_select.options] == list(SKIN_ORDER)


# -- верхняя панель -------------------------------------------------------


def test_topbar_has_tiles_button(app):
    scene = GameScene(app)
    by_icon = {button.icon: button for button in scene.buttons}
    assert 'tiles' in by_icon
    assert by_icon['tiles'].label in {skin.title for skin in SKINS.values()}


def test_topbar_tiles_button_cycles_skin(app):
    scene = GameScene(app)
    app.ctx.set_tiles('bone')
    scene.btn_tiles.label = SKINS['bone'].title

    _click(scene.btn_tiles)

    assert app.ctx.tiles == 'graphite'
    assert scene.btn_tiles.label == SKINS['graphite'].title
    app.ctx.set_tiles('bone')


def test_topbar_buttons_fit_the_window(app):
    """Четыре кнопки обязаны поместиться в верхнюю панель без наездов."""
    from domino import settings

    scene = GameScene(app)
    assert len(scene.buttons) == 4
    for index, first in enumerate(scene.buttons):
        assert first.rect.left >= 0, f'{first.icon} вылез за левый край'
        assert first.rect.right <= settings.W - settings.BOARD_MARGIN
        for second in scene.buttons[index + 1:]:
            assert not first.rect.colliderect(second.rect), (
                f'{first.icon} и {second.icon} перекрываются'
            )


def test_topbar_tiles_button_does_not_overlap_score(app):
    """Кнопка костей не должна заезжать на счёт и индикатор хода."""
    scene = GameScene(app)
    # Счёт (200..312) и индикатор хода (330..520) — заведомо левее кнопок.
    assert scene.btn_tiles.rect.left > 520


# -- пауза ----------------------------------------------------------------


def test_pause_has_tiles_button(app):
    pause = PauseScene(app)
    labels = [button.label for button in pause.buttons]
    assert any(label.startswith('Кости:') for label in labels), labels


def test_pause_tiles_button_cycles_skin(app):
    pause = PauseScene(app)
    app.ctx.set_tiles('bone')

    tiles_button = next(b for b in pause.buttons if b.label.startswith('Кости:'))
    _click(tiles_button)
    pause.update(0.016)

    assert app.ctx.tiles == 'graphite'
    assert tiles_button.label == f'Кости: {SKINS["graphite"].title}'
    app.ctx.set_tiles('bone')


def test_pause_buttons_do_not_overlap(app):
    pause = PauseScene(app)
    for index, first in enumerate(pause.buttons):
        assert pause.rect.contains(first.rect), f'{first.label} выходит за панель'
        for second in pause.buttons[index + 1:]:
            assert not first.rect.colliderect(second.rect), (
                f'{first.label} и {second.label} перекрываются'
            )



def test_pause_panel_fits_the_window(app):
    from domino import settings

    pause = PauseScene(app)
    assert pause.rect.top >= settings.TOPBAR_H
    assert pause.rect.bottom <= settings.H


# -- отрисовка ------------------------------------------------------------


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_game_draws_with_every_skin(app, skin_key):
    app.ctx.set_tiles(skin_key)
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(app.screen)
    pause = PauseScene(app)
    pause.update(0.016)
    pause.draw(app.screen)
    app.ctx.set_tiles('bone')


@pytest.mark.parametrize('skin_key', SKIN_ORDER)
def test_menu_draws_with_every_skin(app, skin_key):
    app.ctx.set_tiles(skin_key)
    scene = MenuScene(app)
    scene.update(0.016)
    scene.draw(app.screen)
    app.ctx.set_tiles('bone')


def test_skin_survives_new_game(app):
    """Смена набора не сбрасывается при переходе в новую партию."""
    app.ctx.set_tiles('amber')
    scene = GameScene(app)
    scene._restart()
    assert app.ctx.tiles == 'amber'
    assert app.ctx.assets.skin.key == 'amber'
    app.ctx.set_tiles('bone')
