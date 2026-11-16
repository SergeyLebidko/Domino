"""Базовый интерфейс стратегии ИИ."""

from __future__ import annotations

import random
from typing import Protocol

from domino.engine import GameState, Move


class Policy(Protocol):
    """Стратегия выбирает один из легальных ходов."""

    name: str

    def choose(self, state: GameState, me: int, rng: random.Random,
               rules=None) -> Move:
        ...


class PolicyBase:
    name = 'base'

    def __init__(self, **options) -> None:
        """Базовый уровень не настраивается, лишние параметры игнорируются."""
        self.options = options

    def choose(self, state: GameState, me: int, rng: random.Random, rules=None) -> Move:
        moves = state.legal_moves(me)
        if not moves:  # pragma: no cover - вызывающий обязан проверить
            raise ValueError('Нет легальных ходов')
        return moves[0]
