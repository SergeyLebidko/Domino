"""Боковая панель: счёт, журнал ходов, подсказки."""

from __future__ import annotations

import math

import pygame as pg

from domino.engine import GameState
from domino.settings import LOG_VISIBLE
from domino.ui.assets import Assets, text_image
from domino.ui.theme import Theme
from domino.ui.widgets import draw_panel, fit_text


class LogEntry:
    __slots__ = ('text', 'kind', 'turn')

    def __init__(self, text: str, kind: str = 'info', turn: int | None = None) -> None:
        self.text = text
        self.kind = kind
        self.turn = turn


class Sidebar:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.log: list[LogEntry] = []
        self.appear = 0.0
        self.scroll = 0

    def add(self, entry: LogEntry) -> None:
        self.log.append(entry)
        del self.log[:-200]
        self.appear = 0.0
        self.scroll = 0

    def update(self, dt: float) -> None:
        self.appear = min(1.0, self.appear + dt * 6.0)

    def draw(
        self,
        surface: pg.Surface,
        rect: pg.Rect,
        theme: Theme,
        state: GameState,
        *,
        scores: tuple[int, int],
        difficulty: str,
        thinking: bool,
        hint: str | None,
        message: str | None = None,
    ) -> None:
        draw_panel(surface, rect, theme, fill=theme.panel, border=theme.panel_edge)
        inner = rect.inflate(-28, -24)
        y = inner.top

        # Счёт
        score_rect = pg.Rect(inner.left, y, inner.width, 84)
        draw_panel(surface, score_rect, theme, fill=theme.panel_alt, radius=theme.radius)
        self._score(surface, theme, score_rect, scores)
        y = score_rect.bottom + 18

        # Журнал
        self._log(surface, theme, pg.Rect(inner.left, y, inner.width, inner.bottom - y - 92), state)

        # Подсказка/сообщение внизу
        footer = pg.Rect(inner.left, inner.bottom - 76, inner.width, 76)
        draw_panel(
            surface,
            footer,
            theme,
            fill=theme.panel_alt if not thinking else theme.panel,
            radius=theme.radius,
        )
        self._footer(surface, theme, footer, state, thinking=thinking, hint=hint, message=message)

    # -- части --------------------------------------------------------------

    def _score(self, surface, theme: Theme, rect: pg.Rect, scores) -> None:
        """Только счёт партий: очки на руках показываются у самих рук."""
        left = rect.left + 16
        font_label = self.assets.body(12, bold=True)
        font_value = self.assets.heading(26)

        label = text_image(font_label, 'СЧЁТ', theme.text_dim)
        surface.blit(label, (left, rect.top + 10))

        # Игрок
        px = left
        py = rect.top + 32
        pg.draw.circle(surface, theme.player, (px + 5, py + 8), 5)
        name = text_image(self.assets.body(14), 'Вы', theme.text)
        surface.blit(name, (px + 18, py))
        value = text_image(font_value, str(scores[0]), theme.text)
        surface.blit(value, (px + 18, py + 16))

        # ИИ
        ai_x = rect.left + rect.width // 2 + 6
        pg.draw.rect(surface, theme.ai, pg.Rect(ai_x, py + 3, 10, 10), border_radius=2)
        name = text_image(self.assets.body(14), 'ИИ', theme.text)
        surface.blit(name, (ai_x + 18, py))
        value = text_image(font_value, str(scores[1]), theme.text)
        surface.blit(value, (ai_x + 18, py + 16))

    def _log(self, surface, theme: Theme, rect: pg.Rect, state: GameState) -> None:
        title = text_image(self.assets.body(13, bold=True), 'ЖУРНАЛ', theme.text_dim)
        surface.blit(title, (rect.left + 2, rect.top))
        y = rect.top + 24

        rows = self.log[-LOG_VISIBLE:]
        font = self.assets.body(14)
        line_height = 26

        if not rows:
            empty = text_image(font, 'Ходы появятся здесь', theme.text_dim)
            surface.blit(empty, (rect.left + 2, y + 6))
            return

        for index, entry in enumerate(rows):
            age = len(rows) - index - 1
            alpha = max(90, 255 - age * 22)
            color = self._entry_color(entry, theme)
            marker_x = rect.left + 2
            marker_y = y + 9
            self._marker(surface, theme, entry, marker_x, marker_y)
            text = fit_text(font, entry.text, rect.width - 26)
            image = text_image(font, text, color).copy()
            if alpha < 255:
                image.set_alpha(alpha)
            surface.blit(image, (rect.left + 20, y))
            y += line_height
            if y > rect.bottom:
                break

    def _marker(self, surface, theme: Theme, entry: LogEntry, x: int, y: int) -> None:
        if entry.kind == 'player':
            pg.draw.circle(surface, theme.player, (x + 4, y), 4)
        elif entry.kind == 'ai':
            pg.draw.rect(surface, theme.ai, pg.Rect(x, y - 4, 9, 9), border_radius=2)
        elif entry.kind == 'draw':
            pg.draw.rect(surface, theme.text_dim, pg.Rect(x, y - 4, 9, 9), 1, border_radius=2)
        elif entry.kind == 'win':
            pg.draw.circle(surface, theme.success, (x + 4, y), 4)
        elif entry.kind == 'lose':
            pg.draw.circle(surface, theme.danger, (x + 4, y), 4)
        else:
            pg.draw.circle(surface, theme.text_dim, (x + 4, y), 2)

    @staticmethod
    def _entry_color(entry: LogEntry, theme: Theme):
        return {
            'player': theme.text,
            'ai': theme.text,
            'draw': theme.text_dim,
            'win': theme.success,
            'lose': theme.danger,
        }.get(entry.kind, theme.text_dim)

    def _footer(
        self,
        surface,
        theme: Theme,
        rect: pg.Rect,
        state: GameState,
        *,
        thinking: bool,
        hint: str | None,
        message: str | None,
    ) -> None:
        if thinking:
            dots = '.' * (1 + int(pg.time.get_ticks() / 320) % 3)
            label = text_image(self.assets.body(15, bold=True), f'ИИ думает{dots}', theme.accent)
            surface.blit(label, (rect.left + 16, rect.top + 14))
            bar = pg.Rect(rect.left + 16, rect.top + 42, rect.width - 32, 4)
            pg.draw.rect(surface, theme.panel, bar, border_radius=2)
            progress = (math.sin(pg.time.get_ticks() / 300) + 1) / 2
            fill = pg.Rect(bar.x, bar.y, int(bar.width * (0.25 + 0.6 * progress)), bar.height)
            pg.draw.rect(surface, theme.accent, fill, border_radius=2)
            return

        text = message or hint
        if state.turn == 0 and not state.legal_moves(0) and not state.bazaar and not message:
            text = 'Ходов нет — пропуск хода'
        if not text:
            text = 'Ваш ход' if state.turn == 0 else 'Ход ИИ'
        font = self.assets.body(15, bold=bool(message))
        color = theme.accent if message else theme.text

        words = text.split()
        lines, current = [], ''
        for word in words:
            trial = f'{current} {word}'.strip()
            if font.size(trial)[0] > rect.width - 32 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)

        y = rect.top + 14
        for line in lines[:3]:
            image = text_image(font, line, color)
            surface.blit(image, (rect.left + 16, y))
            y += 22
