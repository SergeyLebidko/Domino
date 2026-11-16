"""Тесты кнопок на экране результата: клик должен срабатывать."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.engine import Outcome  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene, MenuScene  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _finished_scene(app) -> GameScene:
    """Сцена с показанным результатом — без долгой партии."""
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.session.outcome = Outcome(0, 'empty_hand', 12)
    scene._sync()

    # Сначала рисуем кадр: обработчик обязан работать и без него, но так
    # повторяется настоящий порядок «кадр отрисовки, затем клик».
    scene.draw(app.screen)
    assert scene.result_shown
    return scene


def _click(app, scene, index: int) -> None:
    """Полный клик: наведение, нажатие, кадр отрисовки, отпускание."""
    button = scene._ensure_result_panel()[index]
    center = button.rect.center

    scene.handle(pg.event.Event(pg.MOUSEMOTION, pos=center, rel=(0, 0), buttons=(0, 0, 0)))
    scene.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=center, button=pg.BUTTON_LEFT))
    # Кадр между нажатием и отпусканием — именно здесь старый код терял клик.
    scene.draw(app.screen)
    scene.handle(pg.event.Event(pg.MOUSEBUTTONUP, pos=center, button=pg.BUTTON_LEFT))


def test_result_panel_is_created_once(app):
    """Регрессия: панель пересоздавалась в _draw_result на каждом кадре."""
    scene = _finished_scene(app)
    first = scene._ensure_result_panel()
    scene.draw(app.screen)
    second = scene._ensure_result_panel()
    assert first is second, 'кнопки результата пересоздаются при отрисовке'
    assert len(second) == 2


def test_play_again_button_restarts(app):
    """Регрессия: клик по «Играть ещё» не работал."""
    scene = _finished_scene(app)

    _click(app, scene, 0)

    assert not scene.result_shown, 'экран результата остался висеть'
    assert scene.session.outcome is None, 'партия не начата заново'
    assert scene.session.log and scene.session.log[-2][0] == 'Новая партия.'


def test_back_to_menu_button_switches_scene(app):
    """Регрессия: клик по «В меню» не работал."""
    scene = _finished_scene(app)
    app.push(lambda _app: scene)

    _click(app, scene, 1)

    assert isinstance(app.scene, MenuScene), f'открылась {type(app.scene).__name__}'
    app.scenes.clear()


def test_hover_reaches_result_buttons(app):
    """Кнопки получают наведение — иначе не подсвечиваются при наведении."""
    scene = _finished_scene(app)
    button = scene._ensure_result_panel()[0]
    assert not button.hovered

    scene.handle(pg.event.Event(
        pg.MOUSEMOTION, pos=button.rect.center, rel=(0, 0), buttons=(0, 0, 0)
    ))
    assert button.hovered

    scene.handle(pg.event.Event(
        pg.MOUSEMOTION, pos=(5, 5), rel=(0, 0), buttons=(0, 0, 0)
    ))
    assert not button.hovered


def test_press_outside_does_not_trigger(app):
    """Нажатие мимо кнопки ничего не делает."""
    scene = _finished_scene(app)
    before = scene.session.revision

    scene.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, pos=(5, 5), button=pg.BUTTON_LEFT))
    scene.handle(pg.event.Event(pg.MOUSEBUTTONUP, pos=(5, 5), button=pg.BUTTON_LEFT))

    assert scene.result_shown
    assert scene.session.revision == before


def test_enter_restarts_partie(app):
    """Клавиатурный путь не сломался: Enter начинает новую партию."""
    scene = _finished_scene(app)
    scene.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0, unicode='\r'))
    assert not scene.result_shown
    assert scene.session.outcome is None


def test_escape_goes_to_menu(app):
    """Клавиатурный путь не сломался: Esc ведёт в меню."""
    scene = _finished_scene(app)
    app.push(lambda _app: scene)

    scene.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE, mod=0, unicode=''))

    assert isinstance(app.scene, MenuScene)
    app.scenes.clear()


def test_play_again_redraws_the_board(app):
    """Регрессия: после «Играть ещё» на экране оставалось поле прошлой партии.

    restart() не увеличивал revision, поэтому _sync выходил сразу и вид не
    обновлялся: доска и рука показывали старую партию.
    """
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.session.ai_min_think = 0.0

    # Доигрываем партию, чтобы на доске было много костей.
    for _ in range(600):
        if scene.session.is_over:
            break
        state = scene.session.state
        moves = state.legal_moves(state.turn)
        if not moves:
            scene.session.draw_tile()
        else:
            scene.session.play_move(moves[0])
        scene._sync()
    assert scene.result_shown
    old_chain = len(scene.board.tiles)
    assert old_chain > 2, 'партия не успела обрасти костями'

    scene.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0, unicode='\r'))

    assert len(scene.board.tiles) == len(scene.session.state.chain) == 1, (
        f'на доске {len(scene.board.tiles)} костей, а в новой партии '
        f'{len(scene.session.state.chain)}'
    )
    assert [view.tile for view in scene.hand.tiles] == list(scene.session.state.hands[0])
    assert scene.session.log[-2][0] == 'Новая партия.'


def test_restart_clears_result_panel(app):
    """После перезапуска панель результата не тянет старое состояние."""
    scene = _finished_scene(app)
    scene._ensure_result_panel()
    scene._restart()
    assert scene.result_panel is None
