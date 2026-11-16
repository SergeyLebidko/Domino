"""Снимки для документации: ``python3 -m tools.docs``.

Создаёт в ``screenshots/`` картинки меню, партии и результата в каждой теме.
"""

from __future__ import annotations

import argparse
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402

from tools.screens import render_game, render_menu, render_result  # noqa: E402

#: (имя файла, тема, рендер)
SHOTS = (
    ('menu.png', 'flat_dark', render_menu),
    ('game.png', 'flat_dark', render_game),
    ('result.png', 'flat_dark', render_result),
    ('menu_club_green.png', 'club_green', render_menu),
    ('game_club_green.png', 'club_green', render_game),
    ('menu_warm_wood.png', 'warm_wood', render_menu),
    ('game_warm_wood.png', 'warm_wood', render_game),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--out', default='screenshots')
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    for name, theme, render in SHOTS:
        path = os.path.join(args.out, name)
        render(theme, path)
        print(path)
    pg.quit()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
