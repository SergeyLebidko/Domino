"""Сильный уровень: глубокий PIMC + точный эндшпиль.

То же ядро, что у «Любителя» (``domino.ai.rollout``), но с большим числом
миров, более глубоким доигрыванием и более широкой обрезкой корневых ходов.
Когда базар пуст, включается точный минимакс: информации достаточно, чтобы
решить позицию наверняка.
"""

from __future__ import annotations

import random
import time
from dataclasses import replace

from domino.ai.base import PolicyBase
from domino.ai.knowledge import Knowledge
from domino.ai.medium import MediumPolicy
from domino.ai.rollout import pimc_choose
from domino.ai.solver import EndgameSolver
from domino.engine import GameState, Move, Rules


class HardPolicy(PolicyBase):
    name = 'hard'

    def __init__(
        self,
        samples: int = 10,
        horizon: int = 16,
        top_k: int = 3,
        min_samples: int = 2,
        time_guard_ms: int | None = None,
        endgame_limit: int = 16,
        static_weight: float = 0.5,
        **options,
    ) -> None:
        super().__init__(**options)
        self.samples = samples
        self.horizon = horizon
        self.top_k = top_k
        self.min_samples = min_samples
        self.time_guard_ms = time_guard_ms
        self.endgame_limit = endgame_limit
        self.static_weight = static_weight
        #: Эвристика используется и для оценки, и для доигрывания.
        self.medium = MediumPolicy()
        #: Диагностика последнего решения.
        self.last_values: list[float] = []
        self.last_samples = 0
        self.last_source = ''

    def choose(
        self,
        state: GameState,
        me: int,
        rng: random.Random,
        rules: Rules | None = None,
    ) -> Move:
        rules = rules or Rules()
        if state.turn != me:
            state = replace(state, turn=me)

        moves = state.legal_moves(me)
        if not moves:  # pragma: no cover - вызывающий обязан проверить
            raise ValueError('Нет легальных ходов')
        if len(moves) == 1:
            return moves[0]

        move = self._solve_endgame(state, rules)
        if move is not None:
            return move

        knowledge = Knowledge.build(state, me)
        static = {move: self.medium.score(state, me, knowledge, move) for move in moves}

        if not knowledge.candidates or not knowledge.opponent_count:
            self.last_source = 'heuristic'
            best = max(static.values())
            return rng.choice([m for m, value in static.items() if value >= best - 1e-9])

        deadline = (
            time.perf_counter() + self.time_guard_ms / 1000.0
            if self.time_guard_ms
            else None
        )
        move, values, done = pimc_choose(
            state,
            me,
            rng,
            rules,
            policy=self.medium,
            static_scores=static,
            samples=self.samples,
            horizon=self.horizon,
            top_k=self.top_k,
            static_weight=self.static_weight,
            min_samples=self.min_samples,
            deadline=deadline,
        )
        self.last_source = 'pimc'
        self.last_values = values
        self.last_samples = done
        return move

    # -- эндшпиль -----------------------------------------------------------

    def _solve_endgame(self, state: GameState, rules: Rules) -> Move | None:
        if state.bazaar:
            return None
        remaining = len(state.hands[0]) + len(state.hands[1])
        if remaining > self.endgame_limit:
            return None
        # Бюджет страхует от патологических позиций: лучше отдать решение
        # эвристике, чем подвесить интерфейс.
        solver = EndgameSolver(rules, time_limit_s=0.35)
        move, values = solver.best(state)
        if move is None:
            return None
        self.last_source = 'solver'
        self.last_values = list(values.values())
        self.last_samples = 0
        # При равной точной оценке сбрасываем более тяжёлую кость.
        target = values.get(move, 0.0)
        best = [m for m in state.legal_moves(state.turn) if values.get(m, -2.0) == target]
        return max(best, key=lambda m: m.tile.pips)
