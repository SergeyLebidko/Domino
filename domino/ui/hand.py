"""Рука игрока: наведение, выбор кости, подсветка концов."""

from __future__ import annotations

import pygame as pg

from domino.engine import GameState
from domino.settings import CELL_HAND, HAND_GAP, W
from domino.ui.assets import Assets, text_image
from domino.ui.theme import Theme
from domino.ui.widgets import approach


class HandTile:
    __slots__ = ('tile', 'rect', 'lift', 'hover', 'selected', 'index', 'playable')

    def __init__(self, tile, index: int) -> None:
        self.tile = tile
        self.index = index
        self.rect = pg.Rect(0, 0, CELL_HAND, 2 * CELL_HAND)
        self.lift = 0.0
        self.hover = 0.0
        self.selected = False
        self.playable = False


class Hand:
    """Нижняя панель с костями игрока."""

    GAP = HAND_GAP
    LIFT = 16

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.tiles: list[HandTile] = []
        self.selected: int | None = None
        self.hovered: int | None = None
        self.panel = pg.Rect(0, 0, 1, 1)
        self._time = 0.0

    def set_hand(self, hand, rect: pg.Rect) -> None:
        self.panel = pg.Rect(rect)
        previous = self.selected_tile
        self.tiles = [HandTile(tile, index) for index, tile in enumerate(hand)]
        # Сохраняем выбор той же кости, если она ещё на руке.
        self.selected = None
        if previous is not None:
            for tile in self.tiles:
                if tile.tile == previous:
                    self.selected = tile.index
                    break

    def layout(self) -> None:
        if not self.tiles:
            return
        count = len(self.tiles)
        width = count * CELL_HAND + (count - 1) * self.GAP
        x = self.panel.centerx - width // 2
        y = self.panel.top + 44
        for tile in self.tiles:
            tile.rect.topleft = (x, y)
            x += CELL_HAND + self.GAP

    def update(self, dt: float, state: GameState, mouse_pos, interactive: bool) -> None:
        self._time += dt
        self.layout()
        legal = {(m.tile, m.side) for m in state.legal_moves(0)} if interactive else set()
        self.hovered = None
        for tile in self.tiles:
            hit = interactive and tile.rect.move(0, -int(tile.lift)).collidepoint(mouse_pos)
            if hit:
                self.hovered = tile.index
            tile.hover = approach(tile.hover, 1.0 if hit else 0.0, 14.0, dt)
            tile.selected = tile.index == self.selected
            target = 0.0
            if tile.selected:
                target = self.LIFT * 0.85
            elif hit:
                target = self.LIFT
            tile.lift = approach(tile.lift, target, 16.0, dt)

            # Подсветка играбельности: маленькая точка под костью.
            playable_left = (tile.tile, 'left') in legal
            playable_right = (tile.tile, 'right') in legal
            tile.playable = playable_left or playable_right if interactive else False

    # -- события ------------------------------------------------------------

    def tile_at(self, pos) -> HandTile | None:
        for tile in self.tiles:
            if tile.rect.move(0, -int(tile.lift)).collidepoint(pos):
                return tile
        return None

    def click(self, pos) -> HandTile | None:
        tile = self.tile_at(pos)
        if tile is None:
            return None
        self.selected = None if self.selected == tile.index else tile.index
        return tile

    def clear_selection(self) -> None:
        self.selected = None

    @property
    def selected_tile(self):
        if self.selected is None or self.selected >= len(self.tiles):
            return None
        return self.tiles[self.selected].tile

    # -- отрисовка ----------------------------------------------------------

    def draw(self, surface: pg.Surface, state: GameState, theme: Theme, interactive: bool) -> None:
        legal_sides = {}
        if interactive:
            for move in state.legal_moves(0):
                legal_sides.setdefault(move.tile, set()).add(move.side)

        for tile in self.tiles:
            y = tile.rect.y - int(tile.lift)
            sprite = self.assets.tile(tile.tile.a, tile.tile.b, True, CELL_HAND)
            if tile.selected:
                glow = self.assets.glow(CELL_HAND, 2 * CELL_HAND)
                surface.blit(glow, (tile.rect.x - 18, y - 18))
            sprite.blit_at(surface, tile.rect.x, y)

            sides = legal_sides.get(tile.tile, set())
            if not sides and interactive:
                dim = pg.Surface((CELL_HAND, 2 * CELL_HAND), pg.SRCALPHA)
                dim.fill((0, 0, 0, 74))
                surface.blit(dim, (tile.rect.x, y))
            elif sides:
                if tile.selected or tile.hover > 0.35:
                    self._draw_targets(surface, theme, tile, y, sides)
                else:
                    self._dot(surface, theme, tile, y)

    @staticmethod
    def _dot(surface: pg.Surface, theme: Theme, tile: HandTile, y: int) -> None:
        """Маленькая точка под костью: эту кость можно поставить."""
        cy = y + 2 * CELL_HAND + 12
        pg.draw.circle(surface, theme.accent, (tile.rect.centerx, cy), 3)

    def _draw_targets(self, surface: pg.Surface, theme: Theme, tile: HandTile, y: int, sides: set[str]) -> None:
        """Подписи-«чипы» у кости: к какому концу её можно поставить."""
        font = self.assets.body(12, bold=True)
        cy = y + 2 * CELL_HAND + 8
        if 'left' in sides:
            self._chip(surface, font, theme, tile.rect.centerx - 5, cy, '◀ слева', align='left')
        if 'right' in sides:
            self._chip(surface, font, theme, tile.rect.centerx + 5, cy, 'справа ▶', align='right')

    @staticmethod
    def _chip(surface, font, theme: Theme, x: int, y: int, label: str, *, align: str) -> None:
        image = text_image(font, label, theme.accent_text)
        rect = pg.Rect(0, 0, image.get_width() + 14, 21)
        if align == 'left':
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        pg.draw.rect(surface, theme.accent, rect, border_radius=10)
        surface.blit(image, image.get_rect(center=rect.center))

    def drop_target(self, pos) -> str | None:
        """Куда игрок бросил кость: 'left'/'right' относительно центра стола."""
        if pos[1] > self.panel.top:
            return None
        return 'left' if pos[0] < W // 2 else 'right'
