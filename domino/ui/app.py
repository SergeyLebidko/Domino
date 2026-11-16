"""Приложение: окно, главный цикл, стек сцен."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import pygame as pg

from domino import settings
from domino.ui.assets import Assets
from domino.ui.theme import get_theme, next_theme


@dataclass
class Context:
    """Общее состояние приложения, доступное сценам."""

    assets: Assets
    theme: str = settings.DEFAULT_THEME
    difficulty: str = settings.DEFAULT_DIFFICULTY
    first_player: int = 0
    scores: list[int] | None = None
    debug: bool = False

    def __post_init__(self) -> None:
        if self.scores is None:
            self.scores = [0, 0]

    @property
    def palette(self):
        return self.assets.theme

    def set_theme(self, key: str) -> None:
        self.theme = key
        self.assets.set_theme(get_theme(key))

    def cycle_theme(self) -> None:
        self.set_theme(next_theme(self.theme).key)


class Scene:
    """Базовая сцена. Приложение хранит стек сцен."""

    def __init__(self, app: 'App') -> None:
        self.app = app

    @property
    def ctx(self) -> Context:
        return self.app.ctx

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def handle(self, event: pg.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pg.Surface) -> None:
        pass


class App:
    def __init__(self, *, theme: str | None = None, difficulty: str | None = None,
                 debug: bool = False, headless: bool = False) -> None:
        pg.init()
        if not headless:
            pg.display.set_caption(settings.WINDOW_TITLE)
            self._set_icon()
        self.screen = self._create_window(headless)
        self.clock = pg.time.Clock()
        self.running = True

        theme = theme or settings.DEFAULT_THEME
        difficulty = difficulty or settings.DEFAULT_DIFFICULTY
        assets = Assets(get_theme(theme), (settings.W, settings.H))
        self.ctx = Context(assets=assets, theme=theme, difficulty=difficulty, debug=debug)

        self.scenes: list[Scene] = []
        self._pending: list[tuple[str, object]] = []

    # -- окно ---------------------------------------------------------------

    def _create_window(self, headless: bool) -> pg.Surface:
        if headless:
            return pg.display.set_mode((settings.W, settings.H))

        # В тестовом/безоконном режиме (SDL_VIDEODRIVER=dummy) масштабирование
        # недоступно: SDL не находит быстрый рендерер и только шумит в лог.
        driver = os.environ.get('SDL_VIDEODRIVER', '').lower()
        can_scale = settings.USE_SCALED and driver not in ('dummy', 'offscreen')
        flags = pg.SCALED if can_scale else 0

        if settings.VSYNC and driver not in ('dummy', 'offscreen'):
            try:
                return pg.display.set_mode(
                    (settings.W, settings.H), flags, vsync=1
                )
            except pg.error:
                pass
        return pg.display.set_mode((settings.W, settings.H), flags)

    def _set_icon(self) -> None:
        size = 32
        icon = pg.Surface((size, size), pg.SRCALPHA)
        pg.draw.rect(icon, (240, 240, 235), (2, 2, 28, 28), border_radius=6)
        pg.draw.line(icon, (60, 60, 60), (16, 5), (16, 27), 2)
        for cx, cy in ((10, 10), (22, 22), (22, 10), (10, 22)):
            pg.draw.circle(icon, (40, 40, 40), (cx, cy), 2)
        pg.display.set_icon(icon)

    # -- сцены --------------------------------------------------------------

    @property
    def scene(self) -> Scene | None:
        return self.scenes[-1] if self.scenes else None

    def push(self, factory) -> None:
        scene = factory(self)
        self.scenes.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        if not self.scenes:
            return
        scene = self.scenes.pop()
        scene.on_exit()
        if self.scenes:
            self.scenes[-1].on_enter()

    def replace(self, factory) -> None:
        while self.scenes:
            self.scenes.pop().on_exit()
        self.push(factory)

    def quit(self) -> None:
        self.running = False

    # -- цикл ---------------------------------------------------------------

    def run(self) -> None:
        while self.running:
            dt = min(0.05, self.clock.tick(settings.FPS) / 1000.0)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                    continue
                if event.type == pg.KEYDOWN and event.key == pg.K_F2:
                    self.ctx.cycle_theme()
                    continue
                scene = self.scene
                if scene is not None:
                    scene.handle(event)

            scene = self.scene
            if scene is not None:
                scene.update(dt)
                scene.draw(self.screen)
            pg.display.flip()

    def stop(self) -> None:
        pg.quit()
        sys.exit(0)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from domino.config import Config

    saved = Config.load()

    parser = argparse.ArgumentParser(description='Домино')
    parser.add_argument('--theme', choices=['flat_dark', 'club_green', 'warm_wood'],
                        default=None, help='визуальная тема')
    parser.add_argument('--difficulty', choices=['easy', 'medium', 'hard'],
                        default=None, help='сложность ИИ')
    parser.add_argument('--skip-menu', action='store_true', help='сразу начать партию')
    parser.add_argument('--debug', action='store_true', help='счётчик FPS')
    args = parser.parse_args(argv)

    app = App(
        theme=args.theme or saved.theme,
        difficulty=args.difficulty or saved.difficulty,
        debug=args.debug,
    )
    app.ctx.first_player = saved.first_player

    from domino.ui.scenes import GameScene, MenuScene

    if args.skip_menu:
        app.push(lambda a: GameScene(a))
    else:
        app.push(lambda a: MenuScene(a))

    try:
        app.run()
    finally:
        Config(
            theme=app.ctx.theme,
            difficulty=app.ctx.difficulty,
            first_player=app.ctx.first_player,
        ).save()
        pg.quit()
    return 0
