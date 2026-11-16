"""Headless-снимки сцен: ``python3 -m tools.screens``.

Рисует меню, игру и результат в каждой теме и сохраняет PNG. Используется для
проверки вёрстки без запуска окна.
"""

from __future__ import annotations

import argparse
import os
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402

from domino.ui.app import App  # noqa: E402
from domino.ui.theme import THEME_ORDER  # noqa: E402


def make_app(theme: str) -> App:
    return App(theme=theme, headless=True)


def render_menu(theme: str, path: str, difficulty: str = 'medium') -> None:
    from domino.ui.scenes import MenuScene

    app = make_app(theme)
    app.ctx.difficulty = difficulty
    scene = MenuScene(app)
    scene.update(0.016)
    scene.draw(app.screen)
    pg.image.save(app.screen, path)


def capture_chain(scene, steps: int = 7, seed: int = 5) -> None:
    """Прокручивает партию до показательной позиции.

    Ищем состояние, в котором цепочка уже длинная, у игрока есть ход и в руке
    достаточно костей, чтобы снимок выглядел как идущая игра.
    """
    session = scene.session
    session.enable_ai = False
    rng = random.Random(seed)

    best = None
    for _ in range(200):
        state = session.state
        moves = state.legal_moves(state.turn)
        if not moves:
            if state.bazaar:
                session.draw_tile()
                scene._sync()
                continue
            break

        if (
            state.turn == 0
            and len(state.chain) >= steps
            and len(state.legal_moves(0)) > 1
            and 3 <= len(state.hands[0]) <= 5
        ):
            best = 'ok'
            break

        if session.is_over or len(state.hands[state.turn]) <= 1:
            break

        session.play_move(moves[rng.randrange(len(moves))])
        scene._sync()

    return best


def render_game(theme: str, path: str, difficulty: str = 'medium', steps: int = 7) -> None:
    from domino.ui.scenes import GameScene

    app = make_app(theme)
    app.ctx.difficulty = difficulty
    app.ctx.first_player = 0
    scene = GameScene(app)
    capture_chain(scene, steps, seed=7)

    scene.board.set_state(scene.session.state)
    scene.board.tiles.clear()
    scene.board.set_state(scene.session.state)
    scene.board.center_all()
    scene.board.camera = scene.board.target_camera
    scene.hand.layout()

    # Выбираем играбельную кость, чтобы на снимке были видны подсказки концов.
    playable = [
        t for t in scene.hand.tiles
        if any(m.tile == t.tile for m in scene.session.legal_moves(0))
    ]
    target = playable[0] if playable else (scene.hand.tiles[0] if scene.hand.tiles else None)
    if target is not None:
        scene.hand.selected = target.index
    for _ in range(6):
        scene.update(0.05)
        if target is not None:
            scene.hand.update(0.05, scene.session.state, target.rect.center, interactive=True)
    scene.draw(app.screen)
    pg.image.save(app.screen, path)


def render_result(theme: str, path: str, difficulty: str = 'medium') -> None:
    from domino.ui.scenes import GameScene

    app = make_app(theme)
    app.ctx.difficulty = difficulty
    scene = GameScene(app)
    session = scene.session
    session.enable_ai = False
    rng = random.Random(3)
    for _ in range(400):
        if session.is_over:
            break
        moves = session.legal_moves(session.state.turn)
        if not moves:
            session.draw_tile()
            continue
        session.play_move(moves[rng.randrange(len(moves))])
    scene._sync()
    for _ in range(3):
        scene.update(0.05)
    scene.draw(app.screen)
    pg.image.save(app.screen, path)


def render_themes(out_dir: str) -> list[str]:
    written = []
    for theme in THEME_ORDER:
        for name, render in (
            ('menu', render_menu),
            ('game', render_game),
            ('result', render_result),
        ):
            path = os.path.join(out_dir, f'{name}_{theme}.png')
            render(theme, path)
            written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--out', default='screenshots/dev')
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for path in render_themes(args.out):
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
