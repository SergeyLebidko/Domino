"""Headless-арена: матчи между стратегиями без pygame.

Используется и тестами, и ручным бенчмарком (``python3 -m tools.arena``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from domino.ai.base import Policy
from domino.engine import Rules, check_game, draw, new_game, play


@dataclass
class Result:
    wins: int = 0
    losses: int = 0
    draws: int = 0
    games: int = 0
    points: int = 0

    def add(self, winner: int) -> None:
        """``winner`` — индекс игрока 0/1 или -1 для ничьей."""
        self.games += 1
        if winner == 0:
            self.wins += 1
        elif winner == 1:
            self.losses += 1
        else:
            self.draws += 1

    @property
    def score(self) -> float:
        """Доля очков (победа = 1, ничья = 0.5)."""
        if not self.games:
            return 0.0
        return (self.wins + 0.5 * self.draws) / self.games

    def __str__(self) -> str:
        return (
            f'{self.wins}W {self.losses}L {self.draws}D '
            f'({self.score:.1%} из {self.games})'
        )


def play_game(
    policies: tuple[Policy, Policy],
    rules: Rules,
    rng: random.Random,
    first_player: int = 0,
    max_steps: int = 400,
) -> int:
    """Играет одну партию. Возвращает 0, 1 или -1 (ничья)."""
    state = new_game(rng, first_player)

    for _ in range(max_steps):
        outcome = check_game(state, rules)
        if outcome is not None:
            return outcome.winner

        player = state.turn
        moves = state.legal_moves(player)
        if not moves:
            state, _ = draw(state, rules)
            continue

        move = policies[player].choose(state, player, rng)
        state = play(state, move)

    return -1


def match(
    policy_a: Policy,
    policy_b: Policy,
    rules: Rules | None = None,
    games: int = 200,
    seed: int = 0,
    alternate_first: bool = True,
) -> Result:
    """Сравнивает две стратегии, попеременно давая каждой ходить первой."""
    rules = rules or Rules()
    result = Result()

    for index in range(games):
        rng = random.Random(seed * 1_000_003 + index)
        first_player = index % 2 if alternate_first else 0
        policies = (policy_a, policy_b)
        winner = play_game(policies, rules, rng, first_player)
        result.add(winner)

    return result
