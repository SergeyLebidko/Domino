"""Отрисовка стола: цепочка костей и камера."""

from __future__ import annotations

import math

import pygame as pg

from domino.engine import GameState
from domino.settings import CELL, CHAIN_GAP
from domino.ui.assets import Assets
from domino.ui.theme import Theme
from domino.ui.widgets import approach, clamp, draw_panel


class PlacedTile:
    """Кость на столе вместе с её положением в мировых координатах."""

    __slots__ = ('slot', 'x', 'y', 'width', 'height', 'index')

    def __init__(self, slot, x: int, y: int, width: int, height: int, index: int) -> None:
        self.slot = slot
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.index = index

    @property
    def rect(self) -> pg.Rect:
        return pg.Rect(self.x, self.y, self.width, self.height)


class Board:
    """Цепочка костей с панорамированием и подсветкой концов."""

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.tiles: list[PlacedTile] = []
        self.chain_left = 0
        self.chain_right = 0
        self.camera = 0.0
        self.target_camera = 0.0
        self.side = 0
        self.manual_until = 0.0
        self.left_glow = 0.0
        self.right_glow = 0.0
        self.highlight_left = False
        self.highlight_right = False
        self.hover_side: str | None = None
        self.pulse = 0.0
        #: Анимация появления последней выложенной кости.
        self.pop_index = -1
        self.pop_t = 1.0
        self._rect = pg.Rect(0, 0, 1, 1)

    # -- геометрия ----------------------------------------------------------

    def set_state(self, state: GameState) -> None:
        previous = len(self.tiles)
        previous_first = self.tiles[0].slot if self.tiles else None
        previous_last = self.tiles[-1].slot if self.tiles else None

        self.tiles = []
        x = 0
        for index, slot in enumerate(state.chain):
            if slot.is_double:
                width, height = CELL, 2 * CELL
            else:
                width, height = 2 * CELL, CELL
            self.tiles.append(PlacedTile(slot, x, -height // 2, width, height, index))
            x += width + CHAIN_GAP

        self.chain_left = 0
        self.chain_right = max(0, x - CHAIN_GAP)
        if self.camera == 0.0:
            self.camera = self.target_camera = self.chain_right / 2

        # Определяем, с какого конца пришла новая кость, и запускаем «выскок».
        if previous and len(self.tiles) == previous + 1:
            if self.tiles[0].slot != previous_first:
                self.pop_index = 0
            elif self.tiles[-1].slot != previous_last:
                self.pop_index = len(self.tiles) - 1
            self.pop_t = 0.0

    @property
    def chain_width(self) -> int:
        return self.chain_right - self.chain_left

    def screen_x(self, world_x: float, rect: pg.Rect) -> float:
        return rect.centerx + (world_x - self.camera)

    # -- камера -------------------------------------------------------------

    def center_on_end(self, side: str, rect: pg.Rect) -> None:
        if not self.tiles:
            return
        tile = self.tiles[0] if side == 'left' else self.tiles[-1]
        self.target_camera = tile.x + tile.width / 2

    def center_on_latest(self) -> None:
        if not self.tiles:
            return
        tile = self.tiles[-1]
        self.target_camera = tile.x + tile.width / 2

    def center_all(self) -> None:
        self.target_camera = (self.chain_left + self.chain_right) / 2

    def scroll(self, direction: int, rect: pg.Rect) -> None:
        step = CELL * (2.5 if direction > 0 else -2.5)
        half = rect.width / 2
        self.target_camera = clamp(
            self.target_camera + step,
            self.chain_left - half * 0.15,
            self.chain_right + half * 0.15,
        )
        self.manual_until = pg.time.get_ticks() / 1000.0 + 1.2

    def update(self, dt: float, rect: pg.Rect, state: GameState) -> None:
        self._rect = rect
        self.camera = approach(self.camera, self.target_camera, 7.0, dt)
        self.pulse = (self.pulse + dt * 2.2) % (2 * math.pi)
        if self.pop_t < 1.0:
            self.pop_t = min(1.0, self.pop_t + dt / 0.24)

        want_left = 1.0 if self.highlight_left else 0.0
        want_right = 1.0 if self.highlight_right else 0.0
        self.left_glow = approach(self.left_glow, want_left, 9.0, dt)
        self.right_glow = approach(self.right_glow, want_right, 9.0, dt)

    def highlight_ends(self, sides) -> None:
        """Подсветить концы, к которым можно пристроить выбранную кость."""
        self.highlight_left = 'left' in sides
        self.highlight_right = 'right' in sides

    def end_rect(self, side: str) -> pg.Rect | None:
        if not self.tiles:
            return None
        tile = self.tiles[0] if side == 'left' else self.tiles[-1]
        x = self.screen_x(tile.x, self._rect)
        return pg.Rect(int(x), self._rect.centery + tile.y, tile.width, tile.height)

    def side_at(self, pos: tuple[int, int], state: GameState) -> str | None:
        """Какая сторона цепочки ближе к точке (для drag&drop)."""
        left = self.end_rect('left')
        right = self.end_rect('right')
        if left is None or right is None:
            return None

        # Цепочка из одной кости: левый и правый концы — одна и та же кость,
        # поэтому делим её пополам.
        if left == right:
            if not left.inflate(20, 20).collidepoint(pos):
                return None
            return 'left' if pos[0] < left.centerx else 'right'

        if left.collidepoint(pos):
            return 'left'
        if right.collidepoint(pos):
            return 'right'
        middle = (left.right + right.left) / 2
        if self._rect.collidepoint(pos):
            return 'left' if pos[0] < middle else 'right'
        return None

    # -- отрисовка ----------------------------------------------------------

    def draw(self, surface: pg.Surface, rect: pg.Rect, state: GameState, theme: Theme) -> None:
        self._rect = rect
        draw_panel(surface, rect, theme, fill=theme.board, border=theme.board_edge, radius=theme.radius + 4)
        self._draw_axis(surface, rect, theme, state)
        self._draw_chain(surface, rect, theme)
        self._draw_ends(surface, rect, theme)

    def _draw_axis(self, surface: pg.Surface, rect: pg.Rect, theme: Theme, state: GameState) -> None:
        """Лёгкие направляющие к краям стола."""
        if not self.tiles:
            return
        y = rect.centery
        color = tuple(min(255, int(c * 1.25)) for c in theme.board)
        half = 40
        view_left = rect.centerx + (self.tiles[0].x - self.camera)
        view_right = rect.centerx + (self.tiles[-1].x + self.tiles[-1].width - self.camera)
        if view_left > rect.left + half:
            pg.draw.line(surface, color, (rect.left + 24, y), (view_left - half, y), 2)
        if view_right < rect.right - half:
            pg.draw.line(surface, color, (view_right + half, y), (rect.right - 24, y), 2)

    def _draw_chain(self, surface: pg.Surface, rect: pg.Rect, theme: Theme) -> None:
        clip = surface.get_clip()
        surface.set_clip(rect.inflate(-6, -6))
        for tile in self.tiles:
            x = self.screen_x(tile.x, rect)
            if x > rect.right or x + tile.width < rect.left:
                continue

            scale = 1.0
            if tile.index == self.pop_index and self.pop_t < 1.0:
                # Лёгкий «выскок» новой кости: от 0.86 до 1.0.
                t = self.pop_t
                scale = 0.86 + 0.14 * (1 - (1 - t) ** 3) + 0.03 * math.sin(t * math.pi)

            sprite = self.assets.tile(
                tile.slot.left,
                tile.slot.right,
                tile.slot.is_double,
                CELL,
            )
            if scale != 1.0:
                image = pg.transform.smoothscale(
                    sprite.surface,
                    (max(1, int(sprite.surface.get_width() * scale)),
                     max(1, int(sprite.surface.get_height() * scale))),
                )
                image.set_alpha(int(255 * min(1.0, self.pop_t * 2.2)))
                cx = x + tile.width / 2
                cy = rect.centery + tile.y + tile.height / 2
                surface.blit(image, image.get_rect(center=(cx, cy)))
            else:
                y = rect.centery + tile.y + (tile.height - sprite.height) // 2
                sprite.blit_at(surface, int(x), int(y))

            if tile.slot.owner >= 0:
                self._draw_owner_marker(surface, theme, tile, x, rect)

        surface.set_clip(clip)

    def _draw_owner_marker(self, surface: pg.Surface, theme: Theme, tile: PlacedTile, x: float, rect: pg.Rect) -> None:
        color = theme.player if tile.slot.owner == 0 else theme.ai
        marker_y = rect.centery + tile.y + tile.height + 7
        width = max(18, tile.width - 10)
        pg.draw.rect(
            surface,
            color,
            pg.Rect(int(x + 5), int(marker_y), int(width), 3),
            border_radius=2,
        )

    def _draw_ends(self, surface: pg.Surface, rect: pg.Rect, theme: Theme, ) -> None:
        for side, strength in (('left', self.left_glow), ('right', self.right_glow)):
            if strength < 0.03:
                continue
            end = self.end_rect(side)
            if end is None:
                continue
            glow = self.assets.glow(end.width, end.height)
            glow.set_alpha(int(255 * strength))
            surface.blit(glow, (end.x - 18, end.y - 18))

            # Изогнутая «скобка» у свободного конца: куда именно ляжет кость.
            color = theme.accent
            width = int(3 * strength) or 1
            if side == 'left':
                x = end.left - 10
                pg.draw.line(surface, color, (x, end.top + 6), (x - 6, end.centery), width)
                pg.draw.line(surface, color, (x - 6, end.centery), (x, end.bottom - 6), width)
            else:
                x = end.right + 10
                pg.draw.line(surface, color, (x, end.top + 6), (x + 6, end.centery), width)
                pg.draw.line(surface, color, (x + 6, end.centery), (x, end.bottom - 6), width)

class ChainAnimation:
    """Кость, летящая из руки или базара в цепочку."""

    def __init__(self, first: int, second: int, vertical: bool, source: tuple[int, int],
                 target: tuple[int, int], duration: float = 0.22) -> None:
        self.first = first
        self.second = second
        self.vertical = vertical
        self.source = source
        self.target = target
        self.duration = duration
        self.elapsed = 0.0

    @property
    def finished(self) -> bool:
        return self.elapsed >= self.duration

    def update(self, dt: float) -> None:
        self.elapsed = min(self.duration, self.elapsed + dt)

    def draw(self, surface: pg.Surface, assets: Assets, cell: int) -> None:
        t = self.elapsed / self.duration
        eased = 1 - (1 - t) ** 3
        x = self.source[0] + (self.target[0] - self.source[0]) * eased
        y = self.source[1] + (self.target[1] - self.source[1]) * eased
        sprite = assets.tile(self.first, self.second, self.vertical, cell)
        sprite.blit_at(surface, int(x), int(y))
