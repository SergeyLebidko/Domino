"""Лёгкий уровень: человекоподобные, но небезупречные ходы."""

from __future__ import annotations

import random

from domino.ai.base import PolicyBase
from domino.ai.knowledge import Knowledge
from domino.engine import GameState, Move, ends_after


class EasyPolicy(PolicyBase):
    """Сбрасывает дубли и тяжёлые кости, но регулярно ошибается."""

    name = 'easy'

    #: Доля «необдуманных» ходов.
    ERROR_RATE = 0.22

    def choose(self, state: GameState, me: int, rng: random.Random, rules=None) -> Move:
        moves = state.legal_moves(me)
        if len(moves) == 1:
            return moves[0]
        if rng.random() < self.ERROR_RATE:
            return rng.choice(moves)

        knowledge = Knowledge.build(state, me)
        return max(moves, key=lambda move: self.rate(state, knowledge, move))

    @staticmethod
    def rate(state: GameState, knowledge: Knowledge, move: Move) -> float:
        score = float(move.tile.pips)
        if move.tile.is_double:
            score += 1.5
            score += 0.5 * sum(1 for slot in state.chain if slot.tile.has(move.tile.a))
        # Лёгкий уровень «видит» только очевидное: не оставлять себе мёртвый конец.
        left, right = ends_after(state.left_end, state.right_end, move)
        score += 0.6 * sum(1 for pip in (left, right) if knowledge.is_dead(pip))
        return score
