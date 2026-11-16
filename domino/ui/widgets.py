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
    """Прямоугольная кнопка со стилями primary / ghost / danger."""

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
    ) -> None:
        self.rect = pg.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.style = style
        self.icon = icon
        self.radius = radius
        self.enabled = enabled
        self.hovered = False
        self.pressed = False

    def handle(self, event: pg.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pg.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
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

        font = assets.body(18 if self.rect.height <= 44 else 20, bold=self.style == 'primary')
        image = font.render(self.label, True, color)
        target = image.get_rect(center=rect.center)
        if self.icon:
            icon_size = 20
            total = image.get_width() + icon_size + 10
            start = rect.centerx - total // 2
            surface.blit(image, (start + icon_size + 10, target.y))
            _draw_icon(surface, self.icon, (start + icon_size // 2, rect.centery), icon_size, color)
        else:
            surface.blit(image, target)


def _draw_icon(
    surface: pg.Surface,
    name: str,
    center: tuple[int, int],
    size: int,
    color: tuple[int, int, int],
) -> None:
    cx, cy = center
    half = size // 2
    if name == 'pause':
        pg.draw.rect(surface, color, (cx - half // 2 - 3, cy - half, 4, size), border_radius=1)
        pg.draw.rect(surface, color, (cx + half // 2 - 1, cy - half, 4, size), border_radius=1)
    elif name == 'menu':
        for i in range(3):
            y = cy - half + i * (size // 2)
            pg.draw.rect(surface, color, (cx - half, y, size, 3), border_radius=1)
    elif name == 'refresh':
        pg.draw.arc(surface, color, (cx - half, cy - half, size, size), 0.6, 5.4, 3)
        pg.draw.polygon(
            surface,
            color,
            [
                (cx + half - 2, cy - half + 2),
                (cx + half + 3, cy - half + 1),
                (cx + half + 1, cy - half + 7),
            ],
        )
    elif name == 'theme':
        pg.draw.aacircle(surface, color, (cx, cy), half, 2)
        pg.draw.rect(surface, color, (cx - 2, cy - half, 4, size))
    elif name == 'close':
        pg.draw.line(surface, color, (cx - half + 2, cy - half + 2), (cx + half - 2, cy + half - 2), 3)
        pg.draw.line(surface, color, (cx + half - 2, cy - half + 2), (cx - half + 2, cy + half - 2), 3)


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
