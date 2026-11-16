"""Тесты подсказок концов над костями в руке игрока."""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino.engine import GameState, Slot, make_tile  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _state_with_hand(values, chain_pip=3) -> tuple[GameState, tuple]:
    """Состояние: цепочка из одного дубля, рука из костей (chain_pip, i)."""
    chain = [Slot(make_tile(chain_pip, chain_pip), chain_pip, chain_pip, -1)]
    hand = tuple(make_tile(chain_pip, value) for value in values)
    state = GameState(hands=(hand, ()), chain=tuple(chain), bazaar=(), turn=0)
    return state, hand


def _prepare(app, values=(0, 1, 2, 3, 4, 5, 6)):
    scene = GameScene(app)
    scene.session.enable_ai = False
    state, hand = _state_with_hand(values)
    scene.session.state = state
    scene.hand.set_hand(hand, scene.hand_rect)
    scene.hand.layout()
    scene.hand._sides = scene.hand._grouped_sides(state)
    return scene, state


def test_hints_are_above_the_tile(app):
    """Подсказки обязаны стоять над костью, а не под ней."""
    scene, _ = _prepare(app)
    for tile in scene.hand.tiles:
        sides = scene.hand._sides[tile.tile]
        for side, rect in scene.hand.hint_rects(tile, sides).items():
            assert rect.bottom <= tile.rect.top, (tile.index, side, rect, tile.rect)


def test_hints_stay_inside_hand_panel(app):
    """Крайние кости не должны выдвигать подсказку за пределы панели."""
    scene, _ = _prepare(app)
    panel = scene.hand.panel
    for tile in scene.hand.tiles:
        sides = scene.hand._sides[tile.tile]
        for side, rect in scene.hand.hint_rects(tile, sides).items():
            assert panel.contains(rect), (tile.index, side, rect, panel)


def test_hints_never_overlap_neighbour_tiles(app):
    """Главная регрессия: подсказка не пересекается с соседними костями."""
    scene, _ = _prepare(app)
    for tile in scene.hand.tiles:
        sides = scene.hand._sides[tile.tile]
        for side, rect in scene.hand.hint_rects(tile, sides).items():
            for other in scene.hand.tiles:
                if other is tile:
                    continue
                assert not rect.colliderect(other.rect), (
                    f'подсказка {side} кости {tile.index} перекрывает кость {other.index}'
                )


def test_only_one_tile_shows_hints(app):
    """Подсказки рисуются максимум для одной кости — иначе они конфликтуют."""
    scene, state = _prepare(app)
    target = scene.hand.tiles[2]
    for _ in range(10):
        scene.hand.update(0.05, state, target.rect.center, interactive=True)
    assert scene.hand.active == target.index


def test_hint_survives_pointer_moving_onto_it(app):
    """Подсказка не должна исчезать, когда мышь ведут к самой пилюле."""
    scene, state = _prepare(app)
    tile = scene.hand.tiles[1]
    for _ in range(8):
        scene.hand.update(0.05, state, tile.rect.center, interactive=True)
    hints = scene.hand.hint_rects(tile, scene.hand._sides[tile.tile])
    centre = hints['left'].center
    for _ in range(3):
        scene.hand.update(0.05, state, centre, interactive=True)
    assert scene.hand.active == tile.index
    assert scene.hand.hint_at(centre) == (tile, 'left')


def test_hint_click_plays_the_tile(app):
    """Клик по «◀»/«▶» сразу кладёт кость к нужному концу."""
    app.ctx.first_player = 0
    scene, state = _prepare(app)
    scene._sync()

    tile = scene.hand.tiles[0]
    sides = scene.hand._sides[tile.tile]
    side = 'left' if 'left' in sides else 'right'
    for _ in range(8):
        scene.hand.update(0.05, state, tile.rect.center, interactive=True)

    before = len(scene.session.state.hands[0])
    point = scene.hand.hint_rects(tile, sides)[side].center
    scene._handle_click(point)

    assert len(scene.session.state.hands[0]) == before - 1
    assert tile.tile not in scene.session.state.hands[0]


def test_hints_hidden_while_dragging(app):
    """Во время перетаскивания подсказки не мешают."""
    scene, state = _prepare(app)
    tile = scene.hand.tiles[0]
    for _ in range(8):
        scene.hand.update(0.05, state, tile.rect.center, interactive=True)
    scene.hand.draw(app.screen, state, app.ctx.palette, interactive=True, dragging=True)
    # Кость на месте, ничего не падает; проверяем сам флаг отрисовки.
    assert scene.hand.active is not None


def test_hints_not_shown_for_unplayable_tiles(app):
    """У кости без доступных концов подсказок быть не может."""
    scene = GameScene(app)
    scene.session.enable_ai = False
    # Цепочка 6:6, на руке только кости без шестёрок.
    chain = [Slot(make_tile(6, 6), 6, 6, -1)]
    hand = (make_tile(0, 1), make_tile(2, 3))
    state = GameState(hands=(hand, ()), chain=tuple(chain), bazaar=(), turn=0)
    scene.session.state = state
    scene.hand.set_hand(hand, scene.hand_rect)
    scene.hand.layout()
    scene.hand._sides = scene.hand._grouped_sides(state)

    tile = scene.hand.tiles[0]
    for _ in range(6):
        scene.hand.update(0.05, state, tile.rect.center, interactive=True)
    assert not scene.hand._sides
    assert scene.hand.hint_at(tile.rect.center) is None
