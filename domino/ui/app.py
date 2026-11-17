"""Приложение: окно, главный цикл, стек сцен."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import pygame as pg

from domino import settings
from domino.ui.assets import Assets
from domino.ui.theme import get_theme, next_theme
from domino.ui.tiles import get_skin, next_skin


@dataclass
class Context:
    """Общее состояние приложения, доступное сценам."""

    assets: Assets
    theme: str = settings.DEFAULT_THEME
    tiles: str = settings.DEFAULT_TILES
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

    @property
    def skin(self):
        """Текущий набор оформления костей."""
        return self.assets.skin

    def set_theme(self, key: str) -> None:
        self.theme = key
        self.assets.set_theme(get_theme(key))

    def cycle_theme(self) -> None:
        self.set_theme(next_theme(self.theme).key)

    def set_tiles(self, key: str) -> None:
        skin = get_skin(key)
        self.tiles = skin.key
        self.assets.set_skin(skin)

    def cycle_tiles(self) -> None:
        self.set_tiles(next_skin(self.tiles).key)


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


def render_app_icon(size: int = 64) -> pg.Surface:
    """Иконка приложения: вертикальная костяшка 1:1.

    Рисуется в 4 раза крупнее и уменьшается сглаживанием — на 16–32 px
    обычные круги и скругления получаются рваными.
    """
    scale = 4
    big = size * scale
    surface = pg.Surface((big, big), pg.SRCALPHA)

    # Поля: кость занимает почти всё поле, но с воздухом по краям.
    width = int(big * 0.64)
    height = int(big * 0.94)
    left = (big - width) // 2
    top = (big - height) // 2
    radius = max(2 * scale, int(big * 0.10))

    face = pg.Rect(left, top, width, height)
    # Кант и лицо: светлая кость с тёмными точками — узнаётся в трее.
    pg.draw.rect(surface, (206, 199, 184), face, border_radius=radius)
    inner = face.inflate(-2 * scale, -2 * scale)
    pg.draw.rect(surface, (247, 243, 233), inner, border_radius=max(1, radius - scale))

    # Перегородка ровно по центру.
    divider = max(scale, big // 48)
    pg.draw.line(surface, (168, 158, 140),
                 (inner.left + width // 8, face.centery),
                 (inner.right - width // 8, face.centery), divider)

    # По одной точке в каждой половинке — кость 1:1.
    pip_radius = max(2 * scale, int(big * 0.085))
    half = height // 4
    for cy in (face.centery - half, face.centery + half):
        _blit_smooth_circle(surface, (40, 45, 54), (face.centerx, cy), pip_radius)

    return pg.transform.smoothscale(surface, (size, size))


def _blit_smooth_circle(
    surface: pg.Surface,
    color: tuple[int, int, int],
    center: tuple[int, int],
    radius: int,
) -> None:
    """Сглаженный круг: два наложенных aacircle дают мягкий край."""
    pg.draw.aacircle(surface, color, center, radius)
    pg.draw.aacircle(surface, color, center, radius - 1)


class App:
    def __init__(self, *, theme: str | None = None, difficulty: str | None = None,
                 tiles: str | None = None, debug: bool = False,
                 headless: bool = False) -> None:
        pg.init()
        if not headless:
            pg.display.set_caption(settings.WINDOW_TITLE)
            self._set_icon()
        self.screen = self._create_window(headless)
        self.clock = pg.time.Clock()
        self.running = True

        theme = theme or settings.DEFAULT_THEME
        difficulty = difficulty or settings.DEFAULT_DIFFICULTY
        tiles = tiles or settings.DEFAULT_TILES
        skin = get_skin(tiles)
        assets = Assets(get_theme(theme), (settings.W, settings.H), skin)
        self.ctx = Context(assets=assets, theme=theme, tiles=skin.key,
                           difficulty=difficulty, debug=debug)

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
        # 64 px: Windows и Linux сами уменьшают до нужного размера в трее,
        # а запас пикселей сохраняет сглаженные края.
        pg.display.set_icon(render_app_icon(64))

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
                if event.type == pg.KEYDOWN and event.key == pg.K_F3:
                    self.ctx.cycle_tiles()
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
    parser.add_argument('--theme',
                        choices=['flat_dark', 'club_green', 'warm_wood', 'linen', 'sky'],
                        default=None, help='визуальная тема стола')
    parser.add_argument('--tiles', choices=['bone', 'graphite', 'amber'],
                        default=None, help='оформление костей')
    parser.add_argument('--difficulty', choices=['easy', 'medium', 'hard'],
                        default=None, help='сложность ИИ')
    parser.add_argument('--skip-menu', action='store_true', help='сразу начать партию')
    parser.add_argument('--debug', action='store_true', help='счётчик FPS')
    args = parser.parse_args(argv)

    app = App(
        theme=args.theme or saved.theme,
        difficulty=args.difficulty or saved.difficulty,
        tiles=args.tiles or saved.tiles,
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
            tiles=app.ctx.tiles,
            difficulty=app.ctx.difficulty,
            first_player=app.ctx.first_player,
        ).save()
        pg.quit()
    return 0
