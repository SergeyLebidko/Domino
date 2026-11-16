"""Анимированный GIF партии: ``python3 -m tools.gif``.

Рендерит несколько ходов в headless-режиме и склеивает их в GIF. Нужен Pillow.
"""

from __future__ import annotations

import argparse
import os
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402

from domino.ui.app import App  # noqa: E402


def capture(theme: str, frames: list[tuple[pg.Surface, int]], steps: int = 10) -> None:
    from domino.ui.scenes import GameScene

    app = App(theme=theme, headless=True)
    app.ctx.first_player = 0
    scene = GameScene(app)
    scene.session.enable_ai = False
    rng = random.Random(9)

    def snap(hold_ms: int = 420) -> None:
        scene.draw(app.screen)
        surface = app.screen.copy()
        frames.append((surface, hold_ms))

    for _ in range(3):
        scene.update(0.05)
    snap(700)

    played = 0
    for _ in range(400):
        if played >= steps or scene.session.is_over:
            break
        state = scene.session.state
        moves = state.legal_moves(state.turn)
        if not moves:
            if state.bazaar:
                scene.session.draw_tile()
                scene._sync()
                for _ in range(3):
                    scene.update(0.05)
                snap(300)
            continue

        move = moves[rng.randrange(len(moves))]
        if state.turn == 0:
            # Выделяем кость, затем ставим — как это делает игрок.
            tile = next((t for t in scene.hand.tiles if t.tile == move.tile), None)
            if tile is not None:
                scene.hand.selected = tile.index
                for _ in range(4):
                    scene.update(0.05)
                    scene.hand.update(0.05, state, tile.rect.center, interactive=True)
                snap(320)
        scene.session.play_move(move)
        scene._sync()
        scene.board.center_on_latest()
        for _ in range(5):
            scene.update(0.05)
        snap(420)
        played += 1

    # Финальный кадр-результат.
    for _ in range(400):
        if scene.session.is_over:
            break
        state = scene.session.state
        moves = state.legal_moves(state.turn)
        if not moves:
            scene.session.draw_tile()
            continue
        scene.session.play_move(moves[0])
    scene._sync()
    for _ in range(3):
        scene.update(0.05)
    snap(1600)


def save_gif(frames: list[tuple[pg.Surface, int]], path: str, scale: float = 0.5) -> None:
    from PIL import Image

    images, durations = [], []
    for surface, hold in frames:
        size = (int(surface.get_width() * scale), int(surface.get_height() * scale))
        scaled = pg.transform.smoothscale(surface, size)
        data = pg.image.tobytes(scaled, 'RGB')
        frame = Image.frombytes('RGB', size, data)
        # Общая палитра на все кадры: GIF иначе «прыгает» цветами и весит больше.
        images.append(frame)
        durations.append(hold)

    palette = images[0].quantize(colors=128, method=Image.MEDIANCUT)
    optimized = [frame.quantize(palette=palette, dither=Image.FLOYDSTEINBERG) for frame in images]

    optimized[0].save(
        path,
        save_all=True,
        append_images=optimized[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--out', default=None, help='путь к GIF')
    parser.add_argument('--theme', default='flat_dark')
    parser.add_argument('--steps', type=int, default=10)
    args = parser.parse_args()

    out = args.out or os.path.join('screenshots', 'play.gif')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)

    frames: list[tuple[pg.Surface, int]] = []
    capture(args.theme, frames, args.steps)
    save_gif(frames, out)
    pg.quit()
    print(f'{out}: {len(frames)} кадров, {os.path.getsize(out) / 1024:.0f} КБ')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
