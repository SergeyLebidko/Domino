"""Мелкие виджеты и общие приёмы рисования."""

from __future__ import annotations

import math
from typing import Callable

import pygame as pg

from domino.ui.assets import Assets, text_image
from domino.ui.theme import Theme


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def approach(current: float, target: float, rate: float, dt: float) -> float:
    """Экспоненциальное сглаживание, независимое от FPS."""
    return current + (target - current) * (1.0 - math.exp(-rate * dt))


def draw_panel(
    surface: pg.Surface,
    rect: pg.Rect,
    theme: Theme,
    *,
    fill: tuple[int, int, int] | None = None,
    border: tuple[int, int, int] | None = None,
    radius: int | None = None,
    border_width: int = 1,
    alpha: int = 255,
) -> None:
    radius = theme.radius if radius is None else radius
    if fill is not None:
        if alpha >= 255:
            pg.draw.rect(surface, fill, rect, border_radius=radius)
        else:
            layer = pg.Surface(rect.size, pg.SRCALPHA)
            pg.draw.rect(layer, (*fill, alpha), layer.get_rect(), border_radius=radius)
            surface.blit(layer, rect.topleft)
    if border is not None:
        pg.draw.rect(surface, border, rect, border_width, border_radius=radius)


def text(
    surface: pg.Surface,
    assets: Assets,
    value: str,
    pos: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
    *,
    bold: bool = False,
    heading: bool = False,
    anchor: str = 'topleft',
) -> pg.Rect:
    font = assets.heading(size) if heading else assets.body(size, bold=bold)
    image = text_image(font, value, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def fit_text(font: pg.font.Font, value: str, max_width: int) -> str:
    if font.size(value)[0] <= max_width:
        return value
    ellipsis = '…'
    trimmed = value
    while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
        trimmed = trimmed[:-1]
    return trimmed + ellipsis


class Button:
    """Прямоугольная кнопка со стилями primary / ghost / danger.

    Если задана ``tooltip``, при наведении над кнопкой появляется подпись —
    это нужно для кнопок-иконок в верхней панели.
    """

    def __init__(
        self,
        rect: pg.Rect,
        label: str,
        on_click: Callable[[], None] | None = None,
        *,
        style: str = 'ghost',
        icon: str | None = None,
        radius: int | None = None,
        enabled: bool = True,
        tooltip: str | None = None,
    ) -> None:
        self.rect = pg.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.style = style
        self.icon = icon
        self.radius = radius
        self.enabled = enabled
        self.tooltip = tooltip
        self.hovered = False
        self.hover_time = 0.0
        self.pressed = False

    def handle(self, event: pg.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pg.MOUSEMOTION:
            was_hovered = self.hovered
            self.hovered = self.rect.collidepoint(event.pos)
            if self.hovered and not was_hovered:
                self.hover_time = 0.0
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pg.MOUSEBUTTONUP and event.button == pg.BUTTON_LEFT:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: pg.Surface, assets: Assets, theme: Theme) -> None:
        radius = theme.radius if self.radius is None else self.radius
        if not self.enabled:
            fill, border = theme.panel, theme.panel_edge
            color = theme.text_dim
        elif self.style == 'primary':
            fill = theme.accent_hover if self.hovered else theme.accent
            if self.pressed:
                fill = theme.accent
            border = None
            color = theme.accent_text
        elif self.style == 'danger':
            fill = theme.panel_alt
            border = theme.danger
            color = theme.danger
        else:
            fill = theme.panel_alt if self.hovered else theme.panel
            border = theme.accent if self.hovered else theme.panel_edge
            color = theme.text

        offset = 1 if self.pressed and self.enabled else 0
        rect = self.rect.move(0, offset)
        draw_panel(surface, rect, theme, fill=fill, border=border, radius=radius)
        if self.style == 'primary' and self.enabled:
            glow = pg.Surface(rect.size, pg.SRCALPHA)
            pg.draw.rect(glow, (*theme.accent, 50), glow.get_rect(), border_radius=radius)
            surface.blit(glow, rect.topleft)

        # Только иконка: рисуем строго по центру кнопки.
        if self.icon and not self.label:
            _draw_icon(surface, self.icon, rect.center, _icon_size(rect), color)
            return

        font = assets.body(18 if self.rect.height <= 44 else 20, bold=self.style == 'primary')
        image = text_image(font, self.label, color)
        if not self.icon:
            surface.blit(image, image.get_rect(center=rect.center))
            return

        # Иконка + подпись: центрируем группу целиком.
        icon_size = _icon_size(rect)
        gap = 10
        total = icon_size + gap + image.get_width()
        start = rect.centerx - total // 2
        _draw_icon(surface, self.icon, (start + icon_size // 2, rect.centery),
                   icon_size, color)
        surface.blit(image, (start + icon_size + gap,
                             image.get_rect(centery=rect.centery).y))


def _icon_size(rect: pg.Rect) -> int:
    """Размер глифа: половина меньшей стороны, но не больше 20 px."""
    return max(12, min(20, min(rect.width, rect.height) // 2))


#: Во сколько раз рисуем глиф крупнее, чтобы потом сгладить уменьшением.
ICON_SUPERSAMPLE = 4


def _draw_icon(
    surface: pg.Surface,
    name: str,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
) -> None:
    """Рисует глиф кнопки, сглаженный суперсэмплингом."""
    scale = ICON_SUPERSAMPLE
    big = size * scale
    layer = pg.Surface((big * 2, big * 2), pg.SRCALPHA)
    origin = (layer.get_width() // 2, layer.get_height() // 2)
    _paint_icon(layer, name, origin, big, (*color, 255))

    smooth = pg.transform.smoothscale(layer, (layer.get_width() // scale,
                                             layer.get_height() // scale))
    surface.blit(smooth, (center[0] - smooth.get_width() // 2,
                          center[1] - smooth.get_height() // 2))


def _paint_icon(
    surface: pg.Surface,
    name: str,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int, int],
) -> None:
    """Глифы кнопок. Все симметричны относительно ``center``."""
    cx, cy = center

    if name == 'pause':
        width = max(3, int(size * 0.20))
        height = int(size * 0.78)
        gap = max(3, int(size * 0.16))
        left = cx - gap / 2 - width
        top = cy - height / 2
        pg.draw.rect(surface, color, (left, top, width, height), border_radius=width // 3)
        pg.draw.rect(surface, color, (cx + gap / 2, top, width, height), border_radius=width // 3)
        return

    if name == 'menu':
        width = int(size * 0.80)
        thickness = max(3, int(size * 0.13))
        spacing = int(size * 0.28)
        left = cx - width / 2
        for index in (-1, 0, 1):
            y = cy + index * spacing - thickness / 2
            pg.draw.rect(surface, color, (left, y, width, thickness),
                         border_radius=thickness // 2)
        return

    if name == 'restart':
        # Круговая стрелка: дуга с разрывом и треугольный наконечник.
        radius = int(size * 0.34)
        thickness = max(3, int(size * 0.13))
        box = pg.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        pg.draw.arc(surface, color, box, math.radians(35), math.radians(320), thickness)

        angle = math.radians(35)
        tip = (cx + radius * math.cos(angle), cy - radius * math.sin(angle))
        head = radius * 0.62
        pg.draw.polygon(
            surface,
            color,
            [
                (tip[0] + head * 0.35, tip[1] - head * 0.55),
                (tip[0] - head * 0.75, tip[1] - head * 0.35),
                (tip[0] + head * 0.05, tip[1] + head * 0.75),
            ],
        )
        return

    if name == 'palette':
        # «Контраст»: круг, левая половина залита — стандартный знак темы.
        radius = int(size * 0.36)
        ring = max(3, int(size * 0.12))
        pg.draw.aacircle(surface, color, (cx, cy), radius, ring)

        # Заливаем левую половину внутри кольца.
        half = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
        pg.draw.circle(half, color, (radius, radius), radius - ring // 2 - 1)
        mask = pg.Rect(radius, 0, radius, radius * 2)
        half.fill((0, 0, 0, 0), mask)
        surface.blit(half, (cx - radius, cy - radius))
        return

    if name == 'close':
        arm = int(size * 0.32)
        width = max(3, int(size * 0.13))
        pg.draw.line(surface, color, (cx - arm, cy - arm), (cx + arm, cy + arm), width)
        pg.draw.line(surface, color, (cx + arm, cy - arm), (cx - arm, cy + arm), width)
        return

    if name == 'tiles':
        # Горизонтальное домино 2:1. Точки на 18 px сливаются с рамкой,
        # поэтому узнаваемость держится на контуре и перегородке.
        width = int(size * 0.94)
        height = int(size * 0.56)
        thickness = max(2, int(size * 0.09))
        rect = pg.Rect(cx - width // 2, cy - height // 2, width, height)
        radius = max(2, min(width, height) // 4)
        pg.draw.rect(surface, color, rect, thickness, border_radius=radius)
        pg.draw.line(surface, color,
                     (cx, rect.top + thickness // 2 + 1),
                     (cx, rect.bottom - thickness // 2 - 1),
                     max(1, thickness - 1))


def icon_button_width(assets: Assets, label: str, font_size: int = 17,
                      padding: int = 26, gap: int = 8) -> int:
    """Ширина кнопки «иконка + подпись» под конкретный текст."""
    text_width = assets.body(font_size, bold=True).size(label)[0]
    return 20 + gap + text_width + padding


def draw_tooltip(
    surface: pg.Surface,
    assets: Assets,
    theme: Theme,
    anchor: pg.Rect,
    value: str,
) -> pg.Rect:
    """Всплывающая подпись под элементом ``anchor``."""
    font = assets.body(14)
    image = text_image(font, value, theme.text)
    rect = pg.Rect(0, 0, image.get_width() + 20, 28)
    rect.midtop = (anchor.centerx, anchor.bottom + 8)

    # Не даём подсказке уехать за край окна.
    screen = surface.get_rect()
    rect.left = max(6, min(rect.left, screen.right - rect.width - 6))

    pg.draw.rect(surface, theme.panel_alt, rect, border_radius=8)
    pg.draw.rect(surface, theme.accent, rect, 1, border_radius=8)
    surface.blit(image, image.get_rect(center=rect.center))
    return rect


class Segmented:
    """Группа взаимоисключающих кнопок (сложность, тема, первый ход)."""

    def __init__(
        self,
        rect: pg.Rect,
        options: list[tuple[str, str]],
        on_change: Callable[[str], None],
        selected: str,
    ) -> None:
        self.rect = pg.Rect(rect)
        self.options = options
        self.on_change = on_change
        self.selected = selected
        self.hover_index = -1
        self.pressed_index = -1

    def option_rect(self, index: int) -> pg.Rect:
        width = self.rect.width / len(self.options)
        x = self.rect.x + int(round(width * index))
        return pg.Rect(x, self.rect.y, int(round(width)), self.rect.height)

    def handle(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEMOTION:
            self.hover_index = -1
            for index in range(len(self.options)):
                if self.option_rect(index).collidepoint(event.pos):
                    self.hover_index = index
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
            for index in range(len(self.options)):
                if self.option_rect(index).collidepoint(event.pos):
                    self.pressed_index = index
                    return True
        elif event.type == pg.MOUSEBUTTONUP and event.button == pg.BUTTON_LEFT:
            index = self.pressed_index
            self.pressed_index = -1
            if index >= 0 and self.option_rect(index).collidepoint(event.pos):
                key = self.options[index][0]
                if key != self.selected:
                    self.selected = key
                    self.on_change(key)
                return True
        return False

    def draw(self, surface: pg.Surface, assets: Assets, theme: Theme) -> None:
        draw_panel(surface, self.rect, theme, fill=theme.panel, border=theme.panel_edge, radius=theme.radius)
        for index, (key, label) in enumerate(self.options):
            rect = self.option_rect(index).inflate(-4, -4)
            active = key == self.selected
            hovered = index == self.hover_index
            if active:
                draw_panel(surface, rect, theme, fill=theme.accent, radius=max(4, theme.radius - 4))
                color = theme.accent_text
            else:
                if hovered:
                    draw_panel(surface, rect, theme, fill=theme.panel_alt, radius=max(4, theme.radius - 4))
                color = theme.text if hovered else theme.text_dim
            font = assets.body(17, bold=active)
            image = font.render(label, True, color)
            surface.blit(image, image.get_rect(center=rect.center))


def draw_badge(
    surface: pg.Surface,
    assets: Assets,
    theme: Theme,
    center: tuple[int, int],
    value: str,
    *,
    radius: int = 16,
    fill: tuple[int, int, int] | None = None,
    color: tuple[int, int, int] | None = None,
) -> pg.Rect:
    fill = theme.panel_alt if fill is None else fill
    color = theme.text if color is None else color
    font = assets.body(15, bold=True)
    width = max(radius * 2, font.size(value)[0] + 18)
    rect = pg.Rect(0, 0, width, radius * 2)
    rect.center = center
    pg.draw.rect(surface, fill, rect, border_radius=radius)
    image = font.render(value, True, color)
    surface.blit(image, image.get_rect(center=rect.center))
    return rect


def draw_pips_count(surface: pg.Surface, assets: Assets, pos: tuple[int, int], value: int, color) -> None:
    """Мини-иконка домино для подписей."""
    rect = pg.Rect(pos[0], pos[1], 34, 18)
    pg.draw.rect(surface, color, rect, 1, border_radius=3)
    pg.draw.line(surface, color, (rect.centerx, rect.y + 3), (rect.centerx, rect.bottom - 3), 1)
    image = assets.body(13, bold=True).render(str(value), True, color)
    surface.blit(image, image.get_rect(center=rect.center))
