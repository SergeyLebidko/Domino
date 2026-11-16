"""Порт исходного ИИ (v1) — нужен только для честного сравнения в бенчмарке."""

from __future__ import annotations

import random

from domino.ai.base import PolicyBase
from domino.engine import GameState, Move, ends_after


class LegacyPolicy(PolicyBase):
    """Три правила из первой версии игры, перенесённые на новый движок."""

    name = 'old'

    def choose(self, state: GameState, me: int, rng: random.Random, rules=None) -> Move:
        moves = state.legal_moves(me)
        if not moves:
            raise ValueError('Нет легальных ходов')
        if len(moves) == 1:
            return moves[0]

        rated = [(self.rating(state, me, move), move) for move in moves]
        best = max(score for score, _ in rated)
        return rng.choice([move for score, move in rated if score == best])

    @staticmethod
    def rating(state: GameState, me: int, move: Move) -> int:
        tile = move.tile
        left, right = ends_after(state.left_end, state.right_end, move)
        rating = 0

        # Правило 1: избавляться от дублей, тем активнее, чем больше костей
        # этой масти уже вышло из игры.
        if tile.is_double:
            rating += sum(1 for slot in state.chain if slot.tile.has(tile.a))

        # Правило 2: ставить масти, которых у нас много — значит, у соперника их мало.
        for slot in state.chain:
            if slot.tile.has(left):
                rating += 1
            if slot.tile.has(right):
                rating += 1
        for own in state.hands[me]:
            if own.has(left):
                rating += 1
            if own.has(right):
                rating += 1

        # Правило 3: повторять концы, на которых соперник не смог ответить.
        absent = state.known_absent[1 - me]
        if absent:
            rating += 2 * len({left, right} & absent)

        return rating
