"""Проверка производительности: кадр, кэш ресурсов, ИИ."""

from __future__ import annotations

import os
import random
import time

import pygame as pg

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from domino import settings  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.scenes import GameScene  # noqa: E402


def measure(label: str, frames: int = 90) -> None:
    app = App(headless=True)
    scene = GameScene(app)
    scene.session.enable_ai = False
    rng = random.Random(4)

    for _ in range(30):
        state = scene.session.state
        moves = state.legal_moves(state.turn)
        if not moves:
            if state.bazaar:
                scene.session.draw_tile()
                scene._sync()
                continue
            break
        scene.session.play_move(moves[rng.randrange(len(moves))])
        scene._sync()

    scene.update(0.016)
    times = []
    for _ in range(frames):
        started = time.perf_counter()
        scene.update(0.016)
        scene.draw(app.screen)
        times.append(time.perf_counter() - started)

    times.sort()
    mean = sum(times) / len(times) * 1000
    p95 = times[int(len(times) * 0.95)] * 1000
    print(f'{label}: кадр {mean:.2f} мс (p95 {p95:.2f} мс), цепочка {len(scene.session.state.chain)}')
    pg.quit()


def theme_switch_cost() -> None:
    from domino.ui.assets import Assets
    from domino.ui.theme import get_theme

    pg.init()
    pg.display.set_mode((10, 10))
    assets = Assets(get_theme('flat_dark'), (settings.W, settings.H))
    assets.background
    started = time.perf_counter()
    assets.set_theme(get_theme('club_green'))
    assets.background
    for first in range(7):
        for second in range(first, 7):
            assets.tile(first, second, True, settings.CELL)
            assets.tile(first, second, False, settings.CELL)
    print(f'смена темы: {(time.perf_counter() - started) * 1000:.0f} мс')
    pg.quit()


if __name__ == '__main__':
    measure('стол')
    theme_switch_cost()
