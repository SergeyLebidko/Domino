"""Рука игрока: наведение, выбор кости, подсказки концов."""

from __future__ import annotations

import pygame as pg

from domino.engine import GameState
from domino.settings import (
    CELL_HAND,
    HAND_GAP,
    HAND_PAD_TOP,
    HINT_GAP,
    HINT_H,
    HINT_W,
    W,
)
from domino.ui.assets import Assets
from domino.ui.theme import Theme
from domino.ui.tiles import luminance
from domino.ui.widgets import approach

#: Стрелки для подсказок левого и правого концов.
HINT_ARROWS = {'left': '◀', 'right': '▶'}

#: Высота треугольника-стрелки в подсказке.
HINT_ARROW_SIZE = 9

#: Во сколько раз рисуем стрелку крупнее перед сглаживанием.
_ARROW_SUPERSAMPLE = 6

#: Насколько приглушать неиграбельные кости (сдвиг яркости).
DIM_STEP = 34


def dim_alpha(theme: Theme, face=(246, 242, 231)) -> int:
    """Прозрачность заливки, дающая одинаковый сдвиг яркости в любой теме.

    Фиксированная чёрная заливка на тёмном столе гасит кость почти вдвое,
    а на светлом почти не видна. Поэтому силу считаем от разницы между
    лицом кости и фоном темы.
    """
    difference = abs(luminance(face) - luminance(theme.bg_bottom))
    if difference < 1:
        return 90
    return max(40, min(190, int(DIM_STEP / difference * 255)))


def _draw_hint_arrow(
    surface: pg.Surface,
    center: tuple[int, int],
    side: str,
    color: tuple[int, int, int],
    size: int,
) -> None:
    """Треугольник-стрелка, отцентрированный по ``center``.

    Рисуется примитивами, а не глифом шрифта: у символов ``◀``/``▶``
    несимметричные поля, из-за чего стрелка съезжала вниз на пару пикселей.
    """
    scale = _ARROW_SUPERSAMPLE
    extent = size * scale
    layer = pg.Surface((extent * 2, extent * 2), pg.SRCALPHA)
    cx = cy = extent

    half_h = extent // 2
    half_w = int(extent * 0.42)
    if side == 'left':
        points = [
            (cx - half_w, cy),
            (cx + half_w, cy - half_h),
            (cx + half_w, cy + half_h),
        ]
    else:
        points = [
            (cx + half_w, cy),
            (cx - half_w, cy - half_h),
            (cx - half_w, cy + half_h),
        ]
    pg.draw.polygon(layer, color, points)

    smooth = pg.transform.smoothscale(
        layer, (layer.get_width() // scale, layer.get_height() // scale)
    )
    surface.blit(smooth, (center[0] - smooth.get_width() // 2,
                          center[1] - smooth.get_height() // 2))


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
        #: Кость, для которой сейчас показаны подсказки концов.
        self.active: int | None = None
        self.panel = pg.Rect(0, 0, 1, 1)
        self.mouse: tuple[int, int] = (0, 0)
        self._time = 0.0
        self._sides: dict = {}
        self._interactive = True

    # -- раскладка ----------------------------------------------------------

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
        y = self.panel.top + HAND_PAD_TOP
        for tile in self.tiles:
            tile.rect.topleft = (x, y)
            x += CELL_HAND + self.GAP

    # -- обновление ---------------------------------------------------------

    def update(self, dt: float, state: GameState, mouse_pos, interactive: bool) -> None:
        self._time += dt
        self.mouse = tuple(mouse_pos)
        self.layout()
        self._interactive = interactive
        self._sides = self._grouped_sides(state)
        legal = {(tile, side) for tile, sides in self._sides.items() for side in sides}

        # Зона наведения = сама кость + подсказки над ней. Иначе между костью
        # и стрелкой остаётся «мёртвая полоса»: ушли с кости — подъём гаснет,
        # кость опускается, и подсказка уезжает вниз быстрее курсора.
        self.hovered = None
        if interactive:
            for tile in self.tiles:
                zone = self._hover_zone(tile, self._sides.get(tile.tile))
                if zone.collidepoint(mouse_pos):
                    self.hovered = tile.index
                    break

        over_hint = self._tile_under_hint(mouse_pos)
        if over_hint is not None:
            self.active = over_hint
        elif self.hovered is not None and self.tiles[self.hovered].tile in self._sides:
            self.active = self.hovered
        else:
            self.active = self.selected

        for tile in self.tiles:
            hit = interactive and (tile.index == self.hovered or tile.index == over_hint)
            tile.hover = approach(tile.hover, 1.0 if hit else 0.0, 14.0, dt)
            tile.selected = tile.index == self.selected
            target = 0.0
            if tile.selected:
                target = self.LIFT * 0.85
            elif hit:
                target = self.LIFT
            tile.lift = approach(tile.lift, target, 16.0, dt)

            tile.playable = interactive and (
                (tile.tile, 'left') in legal or (tile.tile, 'right') in legal
            )

    def _hover_zone(self, tile: HandTile, sides) -> pg.Rect:
        """Прямоугольник наведения: кость вместе с подсказками над ней."""
        zone = tile.rect.move(0, -int(tile.lift))
        if sides:
            for rect in self.hint_rects(tile, sides).values():
                zone.union_ip(rect)
        return zone.inflate(2, 2)

    @staticmethod
    def _grouped_sides(state: GameState) -> dict:
        """Доступные концы по каждой кости руки."""
        grouped: dict = {}
        for move in state.legal_moves(0):
            grouped.setdefault(move.tile, set()).add(move.side)
        return grouped

    # -- геометрия подсказок ------------------------------------------------

    def hint_rects(self, tile: HandTile, sides) -> dict[str, pg.Rect]:
        """Прямоугольники подсказок над костью: слева и/или справа."""
        top = tile.rect.y - int(tile.lift) - HINT_H - HINT_GAP
        top = max(self.panel.top + 2, top)

        rects: dict[str, pg.Rect] = {}
        if 'left' in sides:
            rects['left'] = pg.Rect(tile.rect.left, top, HINT_W, HINT_H)
        if 'right' in sides:
            rects['right'] = pg.Rect(tile.rect.right - HINT_W, top, HINT_W, HINT_H)

        # Пилюли не должны выезжать за панель руки.
        low, high = self.panel.left + 3, self.panel.right - HINT_W - 3
        for rect in rects.values():
            rect.left = max(low, min(rect.left, high))
        return rects

    def _tile_under_hint(self, pos) -> int | None:
        """Индекс кости, чья подсказка находится под курсором."""
        candidates = []
        if self.hovered is not None:
            candidates.append(self.hovered)
        if self.selected is not None:
            candidates.append(self.selected)
        if self.active is not None:
            candidates.append(self.active)
        for index in dict.fromkeys(candidates):
            if index >= len(self.tiles):
                continue
            tile = self.tiles[index]
            sides = self._sides.get(tile.tile)
            if not sides:
                continue
            for rect in self.hint_rects(tile, sides).values():
                if rect.inflate(4, 4).collidepoint(pos):
                    return index
        return None

    def hint_at(self, pos) -> tuple[HandTile, str] | None:
        """Подсказка под курсором: (кость, 'left'|'right') или None.

        Проверяются все кости, для которых подсказка могла бы быть показана,
        чтобы клик срабатывал и в тот кадр, когда курсор только подвели.
        """
        if not getattr(self, '_interactive', True):
            return None
        for tile in self.tiles:
            sides = self._sides.get(tile.tile)
            if not sides:
                continue
            for side, rect in self.hint_rects(tile, sides).items():
                if rect.inflate(4, 4).collidepoint(pos):
                    return tile, side
        return None

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

    def draw(
        self,
        surface: pg.Surface,
        state: GameState,
        theme: Theme,
        interactive: bool,
        dragging: bool = False,
    ) -> None:
        grouped = self._sides if self._sides else self._grouped_sides(state)

        # Проход 1: кости. Подсказки здесь не рисуются, иначе соседняя кость
        # ложится поверх пилюли предыдущей.
        for tile in self.tiles:
            y = tile.rect.y - int(tile.lift)
            sprite = self.assets.tile(tile.tile.a, tile.tile.b, True, CELL_HAND)
            if tile.selected:
                glow = self.assets.glow(CELL_HAND, 2 * CELL_HAND)
                surface.blit(glow, (tile.rect.x - 18, y - 18))
            sprite.blit_at(surface, tile.rect.x, y)

            sides = grouped.get(tile.tile, set())
            if not sides and interactive:
                # Неиграбельные кости приглушаются. Чёрная заливка годится
                # только для тёмных тем: на светлом столе она превращает
                # кость в грязно-серое пятно. Силу берём так, чтобы сдвиг
                # яркости был одинаковым на светлом и тёмном столе.
                dim = pg.Surface((CELL_HAND, 2 * CELL_HAND), pg.SRCALPHA)
                dim.fill((*theme.bg_bottom, dim_alpha(theme, self.assets.skin.face)))
                surface.blit(dim, (tile.rect.x, y))
            elif sides and tile.index != self.active:
                self._dot(surface, theme, tile, y)

        # Проход 2: подсказки только для одной активной кости — поверх всего.
        if not interactive or dragging:
            return
        if self.active is None or self.active >= len(self.tiles):
            return
        tile = self.tiles[self.active]
        sides = grouped.get(tile.tile)
        if sides:
            self._draw_hints(surface, theme, tile, sides)

    @staticmethod
    def _dot(surface: pg.Surface, theme: Theme, tile: HandTile, y: int) -> None:
        """Маленькая точка под костью: эту кость можно поставить."""
        cy = y + 2 * CELL_HAND + 12
        pg.draw.circle(surface, theme.accent, (tile.rect.centerx, cy), 3)

    def _draw_hints(self, surface: pg.Surface, theme: Theme, tile: HandTile, sides) -> None:
        for side, rect in self.hint_rects(tile, sides).items():
            pg.draw.rect(surface, theme.accent, rect, border_radius=HINT_H // 2)
            _draw_hint_arrow(surface, rect.center, side, theme.accent_text, HINT_ARROW_SIZE)

    def drop_target(self, pos) -> str | None:
        """Куда игрок бросил кость: 'left'/'right' относительно центра стола."""
        if pos[1] > self.panel.top:
            return None
        return 'left' if pos[0] < W // 2 else 'right'
