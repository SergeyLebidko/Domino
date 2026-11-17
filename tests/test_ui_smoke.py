"""Дымовые тесты интерфейса: сцены рисуются, партия доигрывается без окон."""

from __future__ import annotations

import os

import pygame as pg
import pytest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from domino import settings  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.theme import THEME_ORDER  # noqa: E402


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def test_app_creates_window(app):
    assert app.screen.get_size() == (settings.W, settings.H)
    assert app.ctx.palette.key == settings.DEFAULT_THEME


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_assets_render_for_every_theme(app, theme):
    from domino.ui.assets import Assets
    from domino.ui.theme import get_theme

    assets = Assets(get_theme(theme), (settings.W, settings.H))
    assert assets.background.get_size() == (settings.W, settings.H)
    sprite = assets.tile(6, 3, True, 56)
    assert sprite.width == 56 and sprite.height == 112
    back = assets.tile_back(34)
    assert back.width == 34 and back.height == 68


def test_bundled_fonts_are_used():
    """Шрифты берутся из папки игры, а не из системы — иначе на Windows нет кириллицы."""
    from domino.ui.assets import Assets, BUNDLED_FONTS, FONT_DIR
    from domino.ui.theme import get_theme

    assert FONT_DIR.is_dir()
    for filename in BUNDLED_FONTS.values():
        assert (FONT_DIR / filename).exists(), filename

    probe = Assets(get_theme('flat_dark'), (10, 10))
    font = probe.body(20)
    expected = pg.font.Font(str(FONT_DIR / BUNDLED_FONTS[('sans', False)]), 20)
    assert font.size('Домино ◀▶') == expected.size('Домино ◀▶')
    # Кириллица и стрелки должны иметь ненулевую ширину.
    assert font.size('Домино')[0] > 20


def test_menu_scene_draws(app):
    from domino.ui.scenes import MenuScene

    scene = MenuScene(app)
    scene.update(0.016)
    scene.draw(app.screen)
    assert len(scene.cards) == 3


def test_theme_switch_invalidates_cache(app):
    from domino.ui.assets import Assets
    from domino.ui.theme import get_theme

    assets = Assets(get_theme('flat_dark'), (100, 100))
    first = assets.background
    assets.set_theme(get_theme('club_green'))
    assert assets.background is not first
    assert assets.background.get_size() == (100, 100)


def test_game_scene_plays_via_clicks(app):
    from domino.ui.scenes import GameScene

    app.ctx.first_player = 0
    app.ctx.difficulty = 'easy'
    scene = GameScene(app)
    scene.session.enable_ai = False
    scene.session.ai_min_think = 0.0

    for _ in range(60):
        if scene.session.is_over:
            break
        state = scene.session.state
        moves = state.legal_moves(0)
        if state.turn == 1:
            scene.session.play_move(moves[0])
            scene._sync()
            continue
        if not moves:
            scene.session.player_draw()
            scene._sync()
            continue
        scene.hand.selected = 0
        scene._try_play(moves[0].side)
    scene._sync()
    scene.update(0.016)
    scene.draw(app.screen)


def test_full_game_with_ai_thread(app):
    """Партия с реальным фоновым ИИ доходит до конца."""
    from domino.ui.scenes import GameScene

    app.ctx.difficulty = 'medium'
    scene = GameScene(app)
    scene.session.enable_ai = True
    scene.session.ai_min_think = 0.0

    import time

    deadline = time.time() + 60
    while not scene.session.is_over and time.time() < deadline:
        if scene.session.state.turn == 0:
            moves = scene.session.legal_moves(0)
            if not moves:
                scene.session.player_draw()
            else:
                scene.session.play_move(moves[0])
        else:
            if not scene.session.ai_thinking:
                scene.session.start_ai_turn()
            scene.session.poll_ai()
        scene.update(0.016)
        scene.draw(app.screen)

    assert scene.session.is_over, 'партия не завершилась'
    assert scene.session.tile_count_ok


def test_result_overlay_draws(app):
    from domino.ui.scenes import GameScene

    app.ctx.difficulty = 'easy'
    scene = GameScene(app)
    scene.session.enable_ai = False

    for _ in range(400):
        if scene.session.is_over:
            break
        moves = scene.session.legal_moves(scene.session.state.turn)
        if not moves:
            scene.session.draw_tile()
            continue
        scene.session.play_move(moves[0])
    scene._sync()
    scene.draw(app.screen)
    assert scene.result_shown
    assert scene.result_panel


def test_pause_scene_draws(app):
    from domino.ui.scenes import GameScene, PauseScene

    scene = GameScene(app)
    pause = PauseScene(app)
    pause.update(0.016)
    pause.draw(app.screen)
    assert len(pause.buttons) == 4
    assert scene.session.tile_count_ok


def test_drag_and_drop_plays_tile(app):
    from domino.ui.scenes import GameScene

    app.ctx.first_player = 0
    # Ищем раздачу, где у игрока точно есть ход.
    for seed in range(20):
        scene = GameScene(app)
        scene.session.enable_ai = False
        scene.update(0.016)
        moves = scene.session.legal_moves(0)
        if moves:
            break
    assert moves, 'не нашлось раздачи с ходом'

    move = moves[0]
    tile = next(t for t in scene.hand.tiles if t.tile == move.tile)
    scene.drag_tile = tile
    target = scene.board.end_rect(move.side)
    assert target is not None
    # При цепочке из одной кости её левая и правая половины — разные концы.
    point = (target.left + 6, target.centery) if move.side == 'left' else (target.right - 6, target.centery)
    scene._handle_release(point)
    assert move.tile not in scene.session.state.hands[0]


def test_keyboard_only_play(app):
    """Партию можно вести без мыши: стрелки + Enter."""
    from domino.ui.scenes import GameScene

    app.ctx.first_player = 0
    scene = GameScene(app)
    scene.session.enable_ai = False

    for _ in range(40):
        if scene.session.is_over:
            break
        if scene.session.state.turn == 1:
            scene.session.play_move(scene.session.legal_moves(1)[0])
            scene._sync()
            continue
        if not scene.session.legal_moves(0):
            scene.session.player_draw()
            scene._sync()
            continue
        scene._move_selection(1)
        before = len(scene.session.state.hands[0])
        scene._confirm()
        if len(scene.session.state.hands[0]) == before:
            break
        scene._sync()
