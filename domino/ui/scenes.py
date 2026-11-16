"""Сцены: меню, игра, пауза, результат."""

from __future__ import annotations

import math
import random

import pygame as pg

from domino import settings
from domino.ai import DIFFICULTY_DESCRIPTIONS, DIFFICULTY_NAMES, DIFFICULTIES
from domino.engine import Move
from domino.settings import CELL_SMALL
from domino.ui.app import Scene
from domino.ui.assets import text_image
from domino.ui.board import Board
from domino.ui.hand import Hand
from domino.ui.session import GameSession
from domino.ui.sidebar import LogEntry, Sidebar
from domino.ui.theme import THEME_ORDER, THEMES
from domino.ui.widgets import Button, Segmented, draw_panel, draw_tooltip, text


class MenuScene(Scene):
    """Стартовое меню: сложность, тема, кто ходит первым."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.title_pulse = 0.0
        self.cards: list[tuple[str, pg.Rect]] = []
        self.hover_card: str | None = None
        self._build()

    def _build(self) -> None:
        w = settings.W
        card_w, card_h = 300, 190
        gap = 26
        total = card_w * 3 + gap * 2
        x = w // 2 - total // 2
        y = 300
        self.cards = [(key, pg.Rect(x + index * (card_w + gap), y, card_w, card_h))
                      for index, key in enumerate(DIFFICULTIES)]

        self.theme_select = Segmented(
            pg.Rect(w // 2 - 260, 548, 520, 46),
            [(key, THEMES[key].title) for key in THEME_ORDER],
            self._set_theme,
            self.ctx.theme,
        )
        self.first_select = Segmented(
            pg.Rect(w // 2 - 260, 626, 520, 46),
            [('0', 'Я хожу первым'), ('1', 'Первым ходит ИИ')],
            self._set_first,
            str(self.ctx.first_player),
        )
        self.start_button = Button(
            pg.Rect(w // 2 - 160, 706, 320, 56),
            'Начать игру',
            self._start,
            style='primary',
            radius=self.ctx.palette.radius + 4,
        )
        self.quit_button = Button(pg.Rect(w // 2 - 90, 782, 180, 42), 'Выход', self.app.quit)

    def _set_theme(self, key: str) -> None:
        self.ctx.set_theme(key)

    def _set_first(self, key: str) -> None:
        self.ctx.first_player = int(key)

    def _start(self) -> None:
        self.app.replace(lambda app: GameScene(app))

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
                self._start()
            elif event.key == pg.K_ESCAPE:
                self.app.quit()
            elif event.key in (pg.K_1, pg.K_2, pg.K_3):
                index = event.key - pg.K_1
                if index < len(DIFFICULTIES):
                    self.ctx.difficulty = DIFFICULTIES[index]
            return

        if event.type == pg.MOUSEMOTION:
            self.hover_card = None
            for key, rect in self.cards:
                if rect.collidepoint(event.pos):
                    self.hover_card = key
        if event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
            for key, rect in self.cards:
                if rect.collidepoint(event.pos):
                    self.ctx.difficulty = key
                    return

        self.theme_select.handle(event)
        self.first_select.handle(event)
        self.start_button.handle(event)
        self.quit_button.handle(event)

    def update(self, dt: float) -> None:
        self.title_pulse += dt

    def draw(self, surface: pg.Surface) -> None:
        theme = self.ctx.palette
        assets = self.ctx.assets
        surface.blit(assets.background, (0, 0))

        # Логотип: две кости.
        logo_rect = pg.Rect(0, 0, settings.W, 200)
        self._draw_logo(surface, assets, theme, logo_rect)

        text(surface, assets, 'ДОМИНО', (settings.W // 2, 214), 22, theme.accent,
             bold=True, anchor='center')
        text(
            surface,
            assets,
            'Классическая игра. Три уровня соперника, три оформления стола.',
            (settings.W // 2, 246),
            17,
            theme.text_dim,
            anchor='center',
        )

        text(surface, assets, 'СЛОЖНОСТЬ', (settings.W // 2 - 470, 276), 13, theme.text_dim, bold=True)
        for key, rect in self.cards:
            self._draw_card(surface, assets, theme, key, rect)

        text(surface, assets, 'ТЕМА ОФОРМЛЕНИЯ', (settings.W // 2 - 260, 524), 13, theme.text_dim, bold=True)
        self.theme_select.draw(surface, assets, theme)
        text(surface, assets, 'ПЕРВЫЙ ХОД', (settings.W // 2 - 260, 602), 13, theme.text_dim, bold=True)
        self.first_select.draw(surface, assets, theme)

        self.start_button.draw(surface, assets, theme)
        self.quit_button.draw(surface, assets, theme)

        text(
            surface,
            assets,
            'Enter — начать   •   F2 — сменить тему   •   Esc — выход',
            (settings.W // 2, settings.H - 24),
            14,
            theme.text_dim,
            anchor='center',
        )

    def _draw_logo(self, surface, assets, theme, area: pg.Rect) -> None:
        bob = math.sin(self.title_pulse * 1.4) * 4
        first = assets.tile(3, 6, False, 46)
        second = assets.tile(6, 6, True, 46)
        first.blit_at(surface, area.centerx - 100, area.centery - 40 + int(bob))
        second.blit_at(surface, area.centerx + 34, area.centery - 46 - int(bob))

        glow = assets.glow(150, 110)
        glow.set_alpha(60)
        surface.blit(glow, (area.centerx - 92, area.centery - 70))

    def _draw_card(self, surface, assets, theme, key: str, rect: pg.Rect) -> None:
        active = key == self.ctx.difficulty
        hovered = key == self.hover_card
        fill = theme.panel_alt if (active or hovered) else theme.panel
        border = theme.accent if active else (theme.panel_edge if not hovered else theme.text_dim)
        if hovered and not active:
            rect = rect.move(0, -3)
        draw_panel(surface, rect, theme, fill=fill, border=border, border_width=2 if active else 1)

        # Мини-визуализация уровня: 1/2/3 «фишки».
        count = DIFFICULTIES.index(key) + 1
        for index in range(3):
            x = rect.left + 24 + index * 18
            y = rect.top + 30
            color = theme.accent if index < count else theme.panel_edge
            pg.draw.rect(surface, color, pg.Rect(x, y, 12, 12), border_radius=3)

        text(surface, assets, DIFFICULTY_NAMES[key], (rect.left + 24, rect.top + 56), 24, theme.text,
             bold=True)
        self._paragraph(surface, assets, DIFFICULTY_DESCRIPTIONS[key],
                        pg.Rect(rect.left + 24, rect.top + 92, rect.width - 48, 80),
                        theme.text_dim, 14)

        if active:
            badge = pg.Rect(rect.right - 40, rect.top + 24, 16, 16)
            pg.draw.circle(surface, theme.accent, badge.center, 8)
            pg.draw.circle(surface, theme.bg_top, badge.center, 4)

    @staticmethod
    def _paragraph(surface, assets, value: str, rect: pg.Rect, color, size: int) -> None:
        font = assets.body(size)
        words = value.split()
        line = ''
        y = rect.top
        for word in words:
            trial = f'{line} {word}'.strip()
            if font.size(trial)[0] > rect.width and line:
                surface.blit(text_image(font, line, color), (rect.left, y))
                y += size + 6
                line = word
            else:
                line = trial
        if line:
            surface.blit(text_image(font, line, color), (rect.left, y))


class GameScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.session = GameSession(
            rules=settings.RULES,
            difficulty=self.ctx.difficulty,
            first_player=self.ctx.first_player,
            seed=random.randrange(1 << 30),
        )
        self.session.scores = list(self.ctx.scores)

        self.assets = self.ctx.assets
        self.board = Board(self.assets)
        self.board.set_state(self.session.state)
        self.hand = Hand(self.assets)
        self.sidebar = Sidebar(self.assets)

        self.drag_tile = None
        self.drag_offset = (0, 0)
        self.drag_pos = (0, 0)
        self.board_hover_side: str | None = None
        self.result_shown = False
        self.result_panel = None
        self.time = 0.0
        self._sync_logs()

        self._layout()
        self._build_buttons()
        self._maybe_start_ai()

    # -- раскладка ------------------------------------------------------------

    def _layout(self) -> None:
        w, h = settings.W, settings.H
        self.topbar = pg.Rect(0, 0, w, settings.TOPBAR_H)
        self.sidebar_rect = pg.Rect(
            w - settings.SIDEBAR_W - settings.BOARD_MARGIN,
            settings.TOPBAR_H + settings.BOARD_MARGIN,
            settings.SIDEBAR_W,
            h - settings.TOPBAR_H - settings.BOARD_MARGIN * 2,
        )
        self.board_rect = pg.Rect(
            settings.BOARD_MARGIN,
            settings.TOPBAR_H + settings.BOARD_MARGIN,
            self.sidebar_rect.left - settings.BOARD_MARGIN * 2,
            h - settings.TOPBAR_H - settings.BOARD_MARGIN - settings.HAND_H,
        )
        self.hand_rect = pg.Rect(
            settings.BOARD_MARGIN,
            h - settings.HAND_H,
            self.board_rect.width,
            settings.HAND_H - 10,
        )
        self.hand.panel = self.hand_rect
        self.bazaar_rect = pg.Rect(0, 0, 150, 40)

    def _build_buttons(self) -> None:
        right = settings.W - settings.BOARD_MARGIN
        height = 36
        top = 14
        gap = 8

        self.btn_pause = Button(
            pg.Rect(right - 118, top, 118, height),
            'Пауза',
            self._open_pause,
            icon='pause',
            radius=10,
        )
        self.btn_restart = Button(
            pg.Rect(right - 118 - 128 - gap, top, 128, height),
            'Заново',
            self._restart,
            icon='restart',
            radius=10,
        )
        self.btn_theme = Button(
            pg.Rect(right - 118 - 128 - 116 - gap * 2, top, 116, height),
            'Тема',
            self._cycle_theme,
            icon='palette',
            radius=10,
        )
        # Порядок слева направо: тема, новая партия, пауза.
        self.buttons = [self.btn_theme, self.btn_restart, self.btn_pause]

    def _cycle_theme(self) -> None:
        self.ctx.cycle_theme()
        self.btn_theme.label = THEMES[self.ctx.theme].title

    # -- данные ---------------------------------------------------------------

    def _sync_logs(self) -> None:
        seen = getattr(self, '_log_seen', 0)
        for text_value, kind, turn in self.session.log[seen:]:
            self.sidebar.add(LogEntry(text_value, kind, turn))
        self._log_seen = len(self.session.log)

    def _sync(self) -> None:
        """Обновляет представление, если состояние партии изменилось."""
        revision = getattr(self, '_revision_seen', -1)
        if revision == self.session.revision:
            return
        self._revision_seen = self.session.revision

        self.board.set_state(self.session.state)
        self.hand.set_hand(self.session.state.hands[0], self.hand_rect)
        self._sync_logs()
        if self.session.is_over:
            self.result_shown = True
            self.ctx.scores = list(self.session.scores)

    def _maybe_start_ai(self) -> None:
        if self.session.state.turn == 1 and not self.session.is_over and not self.result_shown:
            self.session.start_ai_turn()

    # -- действия -------------------------------------------------------------

    def _restart(self) -> None:
        self.session.restart()
        self.ctx.first_player = self.session.state.turn
        self.result_shown = False
        self._log_seen = 0
        self.sidebar.log.clear()
        self.hand.clear_selection()
        self._sync()
        self._maybe_start_ai()

    def _open_pause(self) -> None:
        self.app.push(lambda app: PauseScene(app))

    def _back_to_menu(self) -> None:
        self.ctx.scores = [0, 0]
        self.app.replace(lambda app: MenuScene(app))

    def _play(self, move: Move) -> None:
        if not self.session.player_move(move):
            return
        self.hand.clear_selection()
        self.drag_tile = None
        self._sync()
        self.board.center_on_latest()
        self._maybe_start_ai()

    def _side_for_selected(self) -> str | None:
        tile = self.hand.selected_tile
        if tile is None:
            return None
        sides = [m.side for m in self.session.legal_moves(0) if m.tile == tile]
        if len(sides) == 1:
            return sides[0]
        return None

    def _try_play(self, side: str) -> bool:
        tile = self.hand.selected_tile
        if tile is None:
            return False
        move = Move(tile, side)
        if move not in self.session.legal_moves(0):
            return False
        self._play(move)
        return True

    # -- события --------------------------------------------------------------

    def handle(self, event: pg.event.Event) -> None:
        if self.result_shown:
            self._handle_result(event)
            return

        for button in self.buttons:
            if button.handle(event):
                return

        if event.type == pg.KEYDOWN:
            self._handle_key(event)
            return

        if event.type == pg.MOUSEWHEEL:
            self.board.scroll(-event.y, self.board_rect)
            return

        if event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
            self._handle_click(event.pos)
        elif event.type == pg.MOUSEBUTTONUP and event.button == pg.BUTTON_LEFT:
            self._handle_release(event.pos)
        elif event.type == pg.MOUSEMOTION:
            self._handle_motion(event.pos)

    def _handle_key(self, event: pg.event.Event) -> None:
        if event.key == pg.K_ESCAPE:
            self._open_pause()
        elif event.key == pg.K_LEFT:
            self.board.scroll(-1, self.board_rect)
        elif event.key == pg.K_RIGHT:
            self.board.scroll(1, self.board_rect)
        elif event.key == pg.K_UP:
            self._move_selection(-1)
        elif event.key == pg.K_DOWN:
            self._move_selection(1)
        elif event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
            self._confirm()
        elif event.key == pg.K_b:
            self._draw_from_bazaar()

    def _move_selection(self, step: int) -> None:
        count = len(self.hand.tiles)
        if not count:
            return
        if self.hand.selected is None:
            self.hand.selected = 0 if step > 0 else count - 1
        else:
            self.hand.selected = (self.hand.selected + step) % count

    def _confirm(self) -> None:
        if self.session.state.turn != 0 or self.session.is_over:
            return
        if self.hand.selected is None:
            self._draw_from_bazaar()
            return
        sides = [m.side for m in self.session.legal_moves(0) if m.tile == self.hand.selected_tile]
        if not sides:
            self._draw_from_bazaar()
            return
        side = sides[0] if len(sides) == 1 else 'right'
        self._try_play(side)

    def _draw_from_bazaar(self) -> None:
        if self.session.player_draw():
            self._sync()
            self._maybe_start_ai()

    def _handle_click(self, pos) -> None:
        if self.bazaar_rect.collidepoint(pos) or self._bazaar_visual().collidepoint(pos):
            self._draw_from_bazaar()
            return

        # Клик по подсказке «◀»/«▶» сразу кладёт кость к нужному концу.
        # Проверяем раньше кости: пилюля лежит вплотную к её краю.
        hint = self.hand.hint_at(pos)
        if hint is not None:
            tile, side = hint
            move = Move(tile.tile, side)
            if move in self.session.legal_moves(0):
                self._play(move)
            return

        tile = self.hand.click(pos)
        if tile is not None:
            self.drag_tile = tile
            self.drag_offset = (pos[0] - tile.rect.x, pos[1] - tile.rect.y + int(tile.lift))
            self.drag_pos = pos
            return

        if self.hand.selected_tile is not None and self.board_rect.collidepoint(pos):
            side = self.board.side_at(pos, self.session.state)
            if side and self._try_play(side):
                return
        self.hand.clear_selection()

    def _handle_release(self, pos) -> None:
        if self.drag_tile is not None:
            tile = self.drag_tile
            self.drag_tile = None
            if not self.board_rect.collidepoint(pos):
                return
            side = self.board.side_at(pos, self.session.state)
            if side is None:
                return
            move = Move(tile.tile, side)
            if move in self.session.legal_moves(0):
                self._play(move)

    def _handle_motion(self, pos) -> None:
        self.drag_pos = pos
        if self.board_rect.collidepoint(pos):
            self.board.hover_side = self.board.side_at(pos, self.session.state)
        else:
            self.board.hover_side = None

    # -- обновление -----------------------------------------------------------

    def update(self, dt: float) -> None:
        self.time += dt
        if not self.result_shown and self.session.poll_ai():
            pass
        if not self.result_shown and self.session.state.turn == 1 and not self.session.ai_thinking:
            self._maybe_start_ai()

        self._sync()
        self._update_end_highlight()
        self.board.update(dt, self.board_rect, self.session.state)
        self.hand.update(dt, self.session.state, pg.mouse.get_pos(),
                         interactive=self.session.state.turn == 0 and not self.session.is_over)
        self.sidebar.update(dt)

    def _update_end_highlight(self) -> None:
        """Подсвечивает концы цепочки, к которым подходит выбранная кость."""
        tile = self.hand.selected_tile
        sides: set[str] = set()
        if tile is not None and self.session.state.turn == 0 and not self.session.is_over:
            sides = {m.side for m in self.session.legal_moves(0) if m.tile == tile}
        elif self.drag_tile is not None:
            sides = {m.side for m in self.session.legal_moves(0) if m.tile == self.drag_tile.tile}
        self.board.highlight_ends(sides)

    # -- отрисовка ------------------------------------------------------------

    def _bazaar_visual(self) -> pg.Rect:
        return pg.Rect(self.board_rect.right - 190, self.topbar.bottom + 6, 168, 50)

    def draw(self, surface: pg.Surface) -> None:
        theme = self.ctx.palette
        assets = self.assets
        surface.blit(assets.background, (0, 0))

        self._draw_topbar(surface, assets, theme)
        self.board.draw(surface, self.board_rect, self.session.state, theme)
        self._draw_opponent(surface, assets, theme)
        self._draw_bazaar(surface, assets, theme)
        self._draw_hand_panel(surface, assets, theme)
        self.sidebar.draw(
            surface,
            self.sidebar_rect,
            theme,
            self.session.state,
            scores=tuple(self.session.scores),
            difficulty=self.session.difficulty,
            thinking=self.session.ai_thinking,
            hint=self.session.hint,
            message='Партия завершена' if self.session.is_over else None,
        )

        if self.drag_tile is not None:
            self._draw_drag(surface, theme)

        if self.result_shown:
            self._draw_result(surface, assets, theme)

        if self.ctx.debug:
            fps = self.app.clock.get_fps()
            text(surface, assets, f'{fps:4.0f} FPS', (12, 8), 14, theme.text_dim)

    def _draw_topbar(self, surface, assets, theme) -> None:
        draw_panel(surface, self.topbar, theme, fill=theme.panel, border=theme.panel_edge, radius=0)
        pg.draw.line(surface, theme.panel_edge, (0, self.topbar.bottom), (settings.W, self.topbar.bottom), 1)

        # Логотип: одна точка вместо дубля 6:6 — при таком размере шесть
        # кружков сливаются в пятно.
        logo = assets.tile(1, 1, True, 16)
        logo.blit_at(surface, 22, 16)
        text(surface, assets, 'ДОМИНО', (66, 22), 20, theme.text, bold=True, heading=True)

        # Счёт
        score_x = 200
        chip = pg.Rect(score_x, 14, 112, 36)
        draw_panel(surface, chip, theme, fill=theme.panel_alt, radius=10)
        pg.draw.circle(surface, theme.player, (chip.left + 18, chip.centery), 5)
        text(surface, assets, str(self.session.scores[0]), (chip.left + 30, chip.centery), 17,
             theme.text, bold=True, anchor='midleft')
        pg.draw.rect(surface, theme.ai, pg.Rect(chip.left + 62, chip.centery - 5, 10, 10), border_radius=2)
        text(surface, assets, str(self.session.scores[1]), (chip.left + 78, chip.centery), 17,
             theme.text, bold=True, anchor='midleft')

        # Индикатор хода
        turn = self.session.state.turn
        if self.session.is_over:
            label, color = 'Партия завершена', theme.text_dim
        elif self.session.ai_thinking:
            dots = '.' * (1 + int(self.time * 2) % 3)
            label, color = f'ИИ думает{dots}', theme.ai
        elif turn == 0:
            label, color = 'Ваш ход', theme.player
        else:
            label, color = 'Ход ИИ', theme.ai

        indicator = pg.Rect(330, 14, 190, 36)
        draw_panel(surface, indicator, theme, fill=theme.panel_alt, radius=10)
        pg.draw.circle(surface, color, (indicator.left + 18, indicator.centery), 5)
        text(surface, assets, label, (indicator.left + 32, indicator.centery), 16, color,
             anchor='midleft')

        # Кнопки
        for button in self.buttons:
            button.draw(surface, assets, theme)
        self._draw_button_tooltips(surface, assets, theme)

    def _draw_button_tooltips(self, surface, assets, theme) -> None:
        """Подпись под кнопкой-иконкой после короткой задержки наведения."""
        for button in self.buttons:
            if not button.hovered or not button.tooltip:
                continue
            button.hover_time += 1 / max(1, settings.FPS)
            if button.hover_time < 0.22:
                continue
            draw_tooltip(surface, assets, theme, button.rect, button.tooltip)

    def _draw_opponent(self, surface, assets, theme) -> None:
        count = len(self.session.state.hands[1])
        if not count:
            return
        area = pg.Rect(self.board_rect.left + 60, self.board_rect.top + 18, 0, 0)
        sprite = assets.tile_back(CELL_SMALL, True)
        for index in range(count):
            x = area.left + index * (CELL_SMALL + 6)
            sprite.blit_at(surface, x, area.top)

        text(surface, assets, f'ИИ · на руках {self.session.state.pips_of(1)}',
             (area.left, area.top + 2 * CELL_SMALL + 26), 13, theme.text_dim)

    def _draw_bazaar(self, surface, assets, theme) -> None:
        rect = self._bazaar_visual()
        state = self.session.state
        active = state.turn == 0 and not state.legal_moves(0) and bool(state.bazaar)
        fill = theme.panel_alt if active else theme.panel
        border = theme.accent if active else theme.panel_edge
        draw_panel(surface, rect, theme, fill=fill, border=border, border_width=2 if active else 1)

        sprite = assets.tile_back(22, True)
        sprite.blit_at(surface, rect.left + 14, rect.top + 3)

        text(surface, assets, 'БАЗАР', (rect.left + 62, rect.top + 8), 11, theme.text_dim, bold=True)
        text(surface, assets, str(state.bazaar_count), (rect.left + 62, rect.top + 22), 20,
             theme.text, bold=True)

        if active:
            pulse = 0.5 + 0.5 * math.sin(self.time * 4)
            glow = assets.glow(rect.width, rect.height)
            glow.set_alpha(int(120 * pulse))
            surface.blit(glow, (rect.x - 18, rect.y - 18))

    def _draw_hand_panel(self, surface, assets, theme) -> None:
        rect = self.hand_rect
        draw_panel(surface, rect, theme, fill=theme.panel, border=theme.panel_edge)

        state = self.session.state
        active = state.turn == 0 and not self.session.is_over
        if not active:
            overlay = pg.Surface(rect.size, pg.SRCALPHA)
            overlay.fill((0, 0, 0, 40))
            surface.blit(overlay, rect.topleft)

        self.hand.draw(surface, state, theme, interactive=active,
                       dragging=self.drag_tile is not None)

        label = f'Ваши кости: {len(state.hands[0])}'
        text(surface, assets, label, (rect.left + 18, rect.top + 12), 13, theme.text_dim, bold=True)
        text(surface, assets, f'на руках {state.pips_of(0)}',
             (rect.left + 150, rect.top + 12), 13, theme.text_dim)

        if not state.hands[0]:
            text(surface, assets, 'Рука пуста', (rect.centerx, rect.centery), 18, theme.text_dim,
                 anchor='center')

    def _draw_drag(self, surface, theme) -> None:
        tile = self.drag_tile
        x = self.drag_pos[0] - self.drag_offset[0]
        y = self.drag_pos[1] - self.drag_offset[1]
        sprite = self.assets.tile(tile.tile.a, tile.tile.b, True, settings.CELL_HAND)
        sprite.surface.set_alpha(220)
        sprite.blit_at(surface, x, y)
        sprite.surface.set_alpha(None)

        if self.board_rect.collidepoint(self.drag_pos):
            side = self.board.side_at(self.drag_pos, self.session.state)
            if side:
                end = self.board.end_rect(side)
                if end:
                    pg.draw.rect(surface, theme.accent, end.inflate(14, 14), 2,
                                 border_radius=theme.tile_radius + 4)

    # -- результат ------------------------------------------------------------

    def _result_rect(self) -> pg.Rect:
        return pg.Rect(0, 0, 540, 360).move(
            settings.W // 2 - 270,
            settings.H // 2 - 200,
        )

    def _handle_result(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE, pg.K_r):
                self._restart()
            elif event.key == pg.K_ESCAPE:
                self._back_to_menu()
            return
        if event.type == pg.MOUSEBUTTONDOWN and self.result_panel:
            for button in self.result_panel:
                if button.handle(event):
                    return

    def _draw_result(self, surface, assets, theme) -> None:
        state = self.session.state
        outcome = self.session.outcome
        dim = pg.Surface((settings.W, settings.H), pg.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))

        rect = self._result_rect()
        draw_panel(surface, rect, theme, fill=theme.panel, border=theme.accent, border_width=2,
                   radius=theme.radius + 6)

        if outcome is None:
            title, color, detail = 'Партия завершена', theme.text, ''
        elif outcome.winner == 0:
            title, color = 'Вы победили!', theme.success
            detail = f'+{max(1, outcome.points)} очков'
        elif outcome.winner == 1:
            title, color = 'ИИ победил', theme.danger
            detail = f'Соперник получает {max(1, outcome.points)} очков'
        else:
            title, color = 'Ничья', theme.text
            detail = 'Очки на руках равны'

        text(surface, assets, title, (rect.centerx, rect.top + 62), 34, color, bold=True,
             heading=True, anchor='center')
        text(surface, assets, detail, (rect.centerx, rect.top + 104), 16, theme.text_dim,
             anchor='center')

        # Очки на руках
        row = pg.Rect(rect.left + 40, rect.top + 128, rect.width - 80, 46)
        draw_panel(surface, row, theme, fill=theme.panel_alt, radius=theme.radius)
        text(surface, assets, 'На руках:', (row.left + 16, row.centery), 14, theme.text_dim,
             anchor='midleft')
        text(surface, assets, f'вы — {state.pips_of(0)}', (row.left + 120, row.centery), 15,
             theme.text, anchor='midleft')
        text(surface, assets, f'ИИ — {state.pips_of(1)}', (row.left + 250, row.centery), 15,
             theme.text, anchor='midleft')

        text(surface, assets, f'Счёт сессии: {self.session.scores[0]} : {self.session.scores[1]}',
             (rect.centerx, row.bottom + 22), 15, theme.text, anchor='center')

        buttons = [
            Button(pg.Rect(rect.left + 40, rect.bottom - 86, 220, 48), 'Играть ещё', self._restart,
                   style='primary'),
            Button(pg.Rect(rect.left + 280, rect.bottom - 86, 220, 48), 'В меню', self._back_to_menu),
        ]
        self.result_panel = buttons
        for button in buttons:
            button.draw(surface, assets, theme)

        text(surface, assets, 'Enter — ещё партия   •   Esc — в меню',
             (rect.centerx, rect.bottom - 20), 12, theme.text_dim, anchor='center')


class PauseScene(Scene):
    """Полупрозрачная пауза поверх игры."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.time = 0.0
        self.rect = pg.Rect(0, 0, 400, 340).move(
            settings.W // 2 - 200,
            settings.H // 2 - 170,
        )
        self.buttons = [
            Button(pg.Rect(self.rect.left + 40, self.rect.top + 110, 320, 50), 'Продолжить',
                   self._resume, style='primary'),
            Button(pg.Rect(self.rect.left + 40, self.rect.top + 172, 320, 50),
                   f'Тема: {THEMES[self.ctx.theme].title}', self.ctx.cycle_theme),
            Button(pg.Rect(self.rect.left + 40, self.rect.top + 234, 320, 50), 'В меню',
                   self._menu),
        ]

    def _resume(self) -> None:
        self.app.pop()

    def _menu(self) -> None:
        self.app.pop()
        self.app.replace(lambda app: MenuScene(app))

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_ESCAPE, pg.K_p):
                self._resume()
            return
        for button in self.buttons:
            if button.handle(event):
                return

    def update(self, dt: float) -> None:
        self.time += dt
        self.buttons[1].label = f'Тема: {THEMES[self.ctx.theme].title}'

    def draw(self, surface: pg.Surface) -> None:
        theme = self.ctx.palette
        assets = self.ctx.assets

        dim = pg.Surface((settings.W, settings.H), pg.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surface.blit(dim, (0, 0))

        draw_panel(surface, self.rect, theme, fill=theme.panel, border=theme.panel_edge,
                   radius=theme.radius + 6)
        text(surface, assets, 'ПАУЗА', (self.rect.centerx, self.rect.top + 54), 28, theme.text,
             bold=True, heading=True, anchor='center')
        for button in self.buttons:
            button.draw(surface, assets, theme)
        text(surface, assets, 'Esc — продолжить   •   F2 — сменить тему',
             (self.rect.centerx, self.rect.bottom - 22), 12, theme.text_dim, anchor='center')
