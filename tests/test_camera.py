"""Тесты камеры: прокрутка к сыгранной кости и пауза перед ходом ИИ."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.engine import Move  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402
from domino.ui.theme import THEME_ORDER  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _scene(app, **kwargs):
    scene = GameScene(app)
    scene.session.enable_ai = kwargs.get('ai', False)
    scene.session.ai_min_think = 0.0
    return scene


def _long_chain_scene(app, steps: int = 14, seed: int = 5):
    """Сцена с цепочкой длиннее поля — тогда камера вообще двигается."""
    import random

    scene = _scene(app)
    rng = random.Random(seed)
    for _ in range(300):
        state = scene.session.state
        if len(state.chain) >= steps:
            break
        moves = state.legal_moves(state.turn)
        if not moves:
            if state.bazaar:
                scene.session.draw_tile()
                scene._sync()
                continue
            break
        scene.session.play_move(moves[rng.randrange(len(moves))])
        scene._sync()
    return scene


def _scene_with_side(app, side: str, seed: int = 5):
    """Ищет раздачу, где у игрока есть ход в нужную сторону."""
    for attempt in range(24):
        scene = _long_chain_scene(app, seed=seed + attempt)
        state = scene.session.state
        # Доводим очередь до игрока.
        for _ in range(40):
            state = scene.session.state
            if state.turn == 0:
                break
            moves = state.legal_moves(1)
            if not moves:
                scene.session.draw_tile()
            else:
                scene.session.play_move(moves[0])
            scene._sync()
        if scene.session.state.turn == 0 and any(
            m.side == side for m in scene.session.legal_moves(0)
        ):
            return scene
    pytest.skip(f'не нашлось раздачи с ходом {side}')



def _synthetic_board(app, chain_len: int = 14):
    """Сцена с заданной длиной цепочки — без зависимости от раздачи."""
    from dataclasses import replace

    from domino.engine import Slot, make_tile

    scene = _scene(app)
    chain = []
    for index in range(chain_len):
        tile = make_tile(index % 7, (index + 3) % 7)
        if index % 4 == 0:
            tile = make_tile(index % 7, index % 7)
        chain.append(Slot(tile, tile.a, tile.b, index % 2))
    # Даём игроку кости, которые точно подходят к обоим концам.
    left_pip = chain[0].left
    right_pip = chain[-1].right
    hand = (make_tile(left_pip, left_pip), make_tile(right_pip, right_pip))
    state = replace(
        scene.session.state,
        chain=tuple(chain),
        hands=(hand, (make_tile(2, 2),)),
        bazaar=(),
        turn=0,
    )
    scene.session.state = state
    scene._sync()
    return scene


def test_camera_follows_played_side_after_move(app):
    """Регрессия: после хода влево камера ехала к правому концу.

    Проверяем через сам _play, а не вспомогательный метод: важно, чтобы
    сцена вела камеру именно туда, куда легла кость.
    """
    from domino.engine import Move

    scene = _synthetic_board(app, chain_len=16)
    scene.session.enable_ai = False
    board = scene.board

    hand = scene.session.state.hands[0]
    left_pip = scene.session.state.left_end
    tile = next(t for t in hand if t.has(left_pip))
    scene._play(Move(tile, 'left'))

    left_tile = board.tiles[0]
    right_tile = board.tiles[-1]
    left_target = left_tile.x + left_tile.width / 2
    right_target = right_tile.x + right_tile.width / 2

    assert abs(board.target_camera - left_target) <= 1, (
        f'после хода влево камера целится в {board.target_camera}, '
        f'левый конец в {left_target}, правый в {right_target}'
    )
    assert abs(board.target_camera - right_target) > 100, 'цель совпала с правым концом' 


def test_center_on_side_differs_between_ends(app):
    """Левый и правый концы дают разные цели — иначе камера бы не двигалась."""
    scene = _synthetic_board(app, chain_len=16)
    board = scene.board

    board.center_on_side('left')
    left_target = board.target_camera
    board.center_on_side('right')
    right_target = board.target_camera

    assert right_target - left_target > 500, 'концы слишком близко для проверки'


def test_ai_waits_for_camera(app):
    """Регрессия: ИИ ходил мгновенно, и поле прыгало дважды подряд."""
    scene = _synthetic_board(app, chain_len=16)
    scene.session.enable_ai = True

    from domino.engine import Move

    scene._play(Move(scene.session.state.hands[0][0], 'left'))
    assert scene._ai_pending, 'ход ИИ должен ждать остановки камеры'

    # Сразу после хода камера далеко от цели — ИИ не должен стартовать.
    scene.board.camera = 0.0
    scene.board.target_camera = 800.0
    scene.update(1 / 60)
    assert scene._ai_pending, 'ИИ стартовал, пока камера ещё ехала'


def test_ai_starts_after_camera_settles(app):
    """После остановки камеры флаг ожидания снимается."""
    scene = _synthetic_board(app, chain_len=16)
    scene.session.enable_ai = True

    from domino.engine import Move

    scene._play(Move(scene.session.state.hands[0][0], 'left'))

    for _ in range(300):
        if not scene._ai_pending:
            break
        scene.update(1 / 60)

    assert not scene._ai_pending, 'флаг ожидания не сбросился'


def test_camera_settled_helper(app):
    """Вспомогательный метод правильно определяет остановку."""
    scene = _scene(app)
    board = scene.board
    board.camera = 100.0
    board.target_camera = 100.0
    assert board.camera_settled()

    board.target_camera = 400.0
    assert not board.camera_settled()

    board.camera = 397.0
    assert board.camera_settled()


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_play_does_not_crash_in_any_theme(app, theme):
    """Правка камеры не ломает отрисовку ни в одной теме."""
    app.ctx.set_theme(theme)
    scene = _synthetic_board(app, chain_len=16)
    scene.session.enable_ai = False

    state = scene.session.state
    tile = state.hands[0][0]
    scene._play(Move(tile, 'left'))
    scene.update(1 / 60)
    # Только проверка, что отрисовка не падает: инвариант «28 костей» здесь
    # не действует, цепочка синтетическая.
    scene.draw(app.screen)
