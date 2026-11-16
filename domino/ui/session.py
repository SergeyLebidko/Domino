"""Игровая сессия: состояние партии, ходы, ИИ в фоновом потоке."""

from __future__ import annotations

import copy
import random
import threading
import time
from dataclasses import dataclass

from domino.ai import DIFFICULTY_NAMES, make_policy_for_ui
from domino.engine import (
    FULL_SET,
    GameState,
    Move,
    Outcome,
    Rules,
    Tile,
    check_game,
    draw,
    new_game,
    play,
)
from domino.settings import AI_MIN_THINK


@dataclass
class AiReply:
    move: Move | None
    drawn: tuple[Tile, ...] = ()
    duration: float = 0.0
    finished_at: float = 0.0


class GameSession:
    """Одна партия: движок + журнал + счёт + фоновый ИИ."""

    def __init__(
        self,
        rules: Rules,
        difficulty: str = 'medium',
        first_player: int = 0,
        seed: int | None = None,
        enable_ai: bool = True,
    ) -> None:
        self.rules = rules
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.state: GameState = new_game(self.rng, first_player)
        self.first_player = first_player
        self.scores = [0, 0]
        self.log: list[tuple[str, str, int | None]] = []
        self.outcome: Outcome | None = None
        self.enable_ai = enable_ai
        self.ai_min_think = AI_MIN_THINK
        self.policy = make_policy_for_ui(difficulty)

        self._thread: threading.Thread | None = None
        self._reply: AiReply | None = None
        self._ai_started_at = 0.0
        #: Сторона последнего хода — по ней интерфейс ведёт камеру.
        self.last_move_side: str | None = None
        self.hint: str | None = None
        self.last_drawn: tuple[Tile, ...] = ()
        #: Номер версии состояния: сцена синхронизирует вид только при изменении.
        self.revision = 0

        self.add_log(f'Партия начата · {DIFFICULTY_NAMES.get(difficulty, difficulty)}', 'info')
        self.add_log(f'Первая кость: {self.state.chain[0].tile}.', 'info')
        if self.state.turn == 1:
            self.add_log('Первым ходит ИИ.', 'ai')
        else:
            self.add_log('Первым ходите вы.', 'player')
        self._refresh_hint()

    # -- журнал -------------------------------------------------------------

    def add_log(self, text: str, kind: str = 'info', turn: int | None = None) -> None:
        self.log.append((text, kind, turn))
        del self.log[:-300]

    def _touch(self) -> None:
        self.revision += 1

    # -- ходы ---------------------------------------------------------------

    @property
    def is_over(self) -> bool:
        return self.outcome is not None

    def legal_moves(self, player: int = 0) -> list[Move]:
        return self.state.legal_moves(player)

    def can_move(self, player: int = 0) -> bool:
        return bool(self.state.legal_moves(player))

    def draw_tile(self) -> tuple[Tile, ...]:
        """Добор текущим игроком. Возвращает взятые кости.

        Если базар пуст и ходов нет, ход просто передаётся сопернику — иначе
        партия зависла бы навсегда.
        """
        if self.is_over:
            return ()
        player = self.state.turn
        before = len(self.state.hands[player])

        if not self.state.bazaar and not self.can_move(player):
            self._pass_turn()
            if player == 0:
                self.add_log('Ходов нет — вы пропускаете ход.', 'draw')
            else:
                self.add_log('ИИ пропускает ход.', 'draw')
            return ()

        self.state, drawn = draw(self.state, self.rules)
        self.last_drawn = drawn
        if drawn:
            if player == 0:
                self.add_log('Вы взяли из базара.', 'draw')
            else:
                self.add_log('ИИ взял из базара.', 'draw')
        elif self.state.turn != player:
            if player == 0:
                self.add_log('Ходов нет — вы пропускаете ход.', 'draw')
            else:
                self.add_log('ИИ пропускает ход.', 'draw')
        assert len(self.state.hands[player]) >= before
        self._after_action()
        return drawn

    def play_move(self, move: Move) -> bool:
        if self.is_over:
            return False
        player = self.state.turn
        if move not in self.state.legal_moves(player):
            return False

        self.state = play(self.state, move)
        self.last_move_side = move.side
        if player == 0:
            self.add_log(f'Вы: {move.tile} {self._side_label(move.side)}', 'player', player)
        else:
            self.add_log(f'ИИ: {move.tile} {self._side_label(move.side)}', 'ai', player)
        self._after_action()
        return True

    def player_move(self, move: Move) -> bool:
        if self.state.turn != 0:
            return False
        return self.play_move(move)

    def player_draw(self) -> bool:
        """Действие игрока «взять из базара» или «пропустить ход».

        Возвращает True, если состояние изменилось (кость взята или ход передан).
        """
        if self.state.turn != 0 or self.is_over:
            return False
        if self.can_move(0):
            return False
        if not self.state.bazaar:
            # Ходов нет и брать нечего — передаём ход, иначе партия зависнет.
            self.draw_tile()
            return True
        self.draw_tile()
        return True

    @staticmethod
    def _side_label(side: str) -> str:
        return 'слева' if side == 'left' else 'справа'

    def _after_action(self) -> None:
        outcome = check_game(self.state, self.rules)
        if outcome is not None:
            self._finish(outcome)
        self._refresh_hint()
        self._touch()

    def _finish(self, outcome: Outcome) -> None:
        self.outcome = outcome
        if outcome.winner == 0:
            self.scores[0] += max(1, outcome.points)
            self.add_log(f'Вы выиграли! +{outcome.points} очков.', 'win')
        elif outcome.winner == 1:
            self.scores[1] += max(1, outcome.points)
            self.add_log(f'ИИ выиграл. +{outcome.points} очков ему.', 'lose')
        else:
            self.add_log('Ничья.', 'info')

    def _refresh_hint(self) -> None:
        if self.is_over:
            self.hint = None
            return
        if self.state.turn == 1:
            self.hint = 'Ход соперника.'
            return
        moves = self.state.legal_moves(0)
        if moves:
            if len(moves) == 1:
                self.hint = 'Наведите на кость и нажмите стрелку ◀ или ▶ над ней.'
            else:
                self.hint = (
                    f'Доступно ходов: {len(moves)}. Стрелка ◀ или ▶ над костью '
                    'кладёт её к нужному концу.'
                )
        elif self.state.bazaar:
            self.hint = 'Нет подходящих костей — возьмите кость из базара.'
        else:
            self.hint = 'Ходов нет. Пропуск хода.'

    # -- ИИ -----------------------------------------------------------------

    @property
    def ai_thinking(self) -> bool:
        """Идёт ли «размышление» — с учётом минимальной паузы."""
        if self._thread is None:
            return False
        if self._thread.is_alive():
            return True
        return time.perf_counter() - self._ai_started_at < self.ai_min_think

    def start_ai_turn(self) -> None:
        """Запускает расчёт хода ИИ в отдельном потоке."""
        if self._thread is not None or self.is_over or not self.enable_ai:
            return
        if self.state.turn != 1:
            return

        if not self.can_move(1):
            # Нет ходов: добор до играбельной кости, а если базар пуст —
            # передача хода (иначе партия зависла бы навсегда).
            self.draw_tile()
            return

        snapshot = copy.deepcopy(self.state)
        rng = random.Random(self.rng.random())
        policy = self.policy
        reply = AiReply(move=None)

        def worker() -> None:
            started = time.perf_counter()
            try:
                reply.move = policy.choose(snapshot, 1, rng, self.rules)
            except Exception:  # pragma: no cover - страховка от падения ИИ
                moves = snapshot.legal_moves(1)
                reply.move = moves[0] if moves else None
            reply.duration = time.perf_counter() - started
            reply.finished_at = time.perf_counter()
            # Запись делается последней: остальные поля к этому моменту готовы.
            self._reply = reply

        self._ai_started_at = time.perf_counter()
        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def poll_ai(self) -> bool:
        """Применяет готовый ход ИИ. Возвращает True, если что-то произошло.

        Никогда не блокирует поток интерфейса: если расчёт закончился раньше
        минимальной паузы «размышления», ход откладывается до следующего кадра.
        """
        if self._thread is None:
            return False
        if self._thread.is_alive():
            return False

        reply = self._reply
        if reply is None:
            self._thread = None
            return False
        if reply.move is None:
            self._thread = None
            self._reply = None
            return False

        # Минимальная пауза, чтобы ход не выглядел мгновенным.
        remaining = self.ai_min_think - (time.perf_counter() - self._ai_started_at)
        if remaining > 0:
            return False

        self._thread = None
        self._reply = None
        if self.is_over or self.state.turn != 1:
            return False
        return self.play_move(reply.move)

    def ai_wait_time(self) -> float:
        if not self._thread:
            return 0.0
        return time.perf_counter() - self._ai_started_at

    def _pass_turn(self) -> None:
        """Передаёт ход сопернику (базар пуст, ходов нет)."""
        from dataclasses import replace

        self.state = replace(
            self.state,
            turn=1 - self.state.turn,
            passes=self.state.passes + 1,
        )
        self._after_action()

    # -- новый раунд --------------------------------------------------------

    def restart(self, first_player: int | None = None) -> None:
        first = self.first_player if first_player is None else first_player
        self.first_player = first
        self.state = new_game(self.rng, first)
        self.outcome = None
        self.log.clear()
        self._thread = None
        self._reply = None
        self.hint = None
        self.add_log('Новая партия.', 'info')
        self.add_log(f'Первая кость: {self.state.chain[0].tile}.', 'info')
        self._refresh_hint()

    def snapshot_scores(self) -> tuple[int, int]:
        return self.scores[0], self.scores[1]

    # -- для тестов и отладки ----------------------------------------------

    def total_tiles(self) -> int:
        tiles = list(self.state.hands[0]) + list(self.state.hands[1]) + list(self.state.bazaar)
        return len(tiles) + len(self.state.chain)

    @property
    def tile_count_ok(self) -> bool:
        return self.total_tiles() == len(FULL_SET)
