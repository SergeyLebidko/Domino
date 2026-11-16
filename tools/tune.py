"""Подбор весов эвристики среднего уровня против конкретных соперников.

Запуск::

    python3 -m tools.tune --games 1500 --opponent old
    python3 -m tools.tune --games 800 --opponent mixed

Используются общие случайные сиды (common random numbers): каждый вариант
весов играет ровно те же раздачи, что и остальные, поэтому сравнение парное и
намного точнее при том же числе партий.
"""

from __future__ import annotations

import argparse
import math
import random
import time
from dataclasses import asdict, dataclass, fields

from domino.ai import make_policy
from domino.ai.legacy import LegacyPolicy
from domino.ai.solver import EndgameSolver
from domino.engine import (
    FULL_SET,
    GameState,
    Rules,
    check_game,
    draw,
    ends_after,
    new_game,
    play,
)


@dataclass
class Weights:
    """Веса оценки хода."""

    #: Штраф за вероятность ответа соперника (сумма по двум концам).
    opp: float = 5.0
    #: Бонус за свои кости к новым концам (гибкость).
    flex: float = 1.0
    #: Бонус за сброс очков.
    dump: float = 0.15
    #: Бонус за дубль.
    dbl: float = 0.4
    #: Бонус за сведение обоих концов к одной масти.
    same: float = 1.2
    #: Бонус, когда соперник не может ответить вообще.
    dead_all: float = 2.5
    #: Бонус, когда у соперника нет ответа на один из концов.
    dead_one: float = 0.6
    #: Бонус за масти, которых у нас много (контроль масти).
    ctrl: float = 0.5
    #: Штраф за «мёртвые» кости на руке в эндшпиле.
    endgame: float = -0.4
    #: Порог размера рук, при котором включается точный решатель (0 — выкл.).
    solver: int = 0


class TunablePolicy:
    name = 'tunable'

    def __init__(self, weights: Weights) -> None:
        self.w = weights
        self.rules = Rules()

    def choose(self, state: GameState, me: int, rng: random.Random, rules=None) -> object:
        moves = state.legal_moves(me)
        if not moves:
            raise ValueError('нет ходов')
        if len(moves) == 1:
            return moves[0]

        if self.w.solver and not state.bazaar:
            if len(state.hands[0]) + len(state.hands[1]) <= self.w.solver:
                move, _ = EndgameSolver(rules or self.rules).best(state)
                if move is not None:
                    return move

        unseen = _unseen(state, me)
        scored = [(self.evaluate(state, me, move, unseen), move) for move in moves]
        best = max(score for score, _ in scored)
        return rng.choice([move for score, move in scored if score >= best - 1e-9])

    def evaluate(self, state: GameState, me: int, move, unseen) -> float:
        w = self.w
        tile = move.tile
        left, right = ends_after(state.left_end, state.right_end, move)
        rest = [t for t in state.hands[me] if t != tile]
        opponent_size = len(state.hands[1 - me])

        def reply_chance(pip: int) -> float:
            count = sum(1 for t in unseen if t.has(pip))
            if count <= 0 or not unseen or not opponent_size:
                return 0.0
            total = math.comb(len(unseen), opponent_size)
            miss = math.comb(len(unseen) - count, opponent_size)
            return 1.0 - miss / total if total else 0.0

        left_p = reply_chance(left)
        right_p = reply_chance(right)

        score = -w.opp * (left_p + right_p)
        if left_p == 0 and right_p == 0:
            score += w.dead_all
        elif left_p == 0 or right_p == 0:
            score += w.dead_one

        score += w.flex * sum(1 for t in rest if t.has(left) or t.has(right))
        score += w.dump * tile.pips
        if tile.is_double:
            score += w.dbl
        if left == right:
            score += w.same

        score += w.ctrl * (
            sum(1 for t in rest if t.has(left)) + sum(1 for t in rest if t.has(right))
        )

        if len(rest) <= 3:
            score += w.endgame * sum(
                1 for t in rest if not (t.has(left) or t.has(right))
            )
        return score


class RandomPolicy:
    name = 'random'

    def choose(self, state, me, rng, rules=None):
        return rng.choice(state.legal_moves(me))


def _unseen(state: GameState, me: int):
    visible = set(state.hands[me]) | {slot.tile for slot in state.chain}
    return [tile for tile in FULL_SET if tile not in visible]


def duel(policy, opponent, games: int, seed: int, rules: Rules) -> float:
    wins = losses = draws = 0
    for index in range(games):
        rng = random.Random(seed * 1_000_003 + index)
        state = new_game(rng, index % 2)
        policy_a, policy_b = policy, opponent
        winner = -1
        for _ in range(600):
            outcome = check_game(state, rules)
            if outcome is not None:
                winner = outcome.winner
                break
            if not state.legal_moves():
                state, _ = draw(state, rules)
                continue
            player = state.turn
            chooser = policy_a if player == 0 else policy_b
            state = play(state, chooser.choose(state, player, rng, rules))
        if winner == 0:
            wins += 1
        elif winner == 1:
            losses += 1
        else:
            draws += 1
    return (wins + 0.5 * draws) / games


OPPONENTS = {
    'random': RandomPolicy,
    'old': LegacyPolicy,
    'medium': lambda: make_policy('medium'),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--games', type=int, default=1500)
    parser.add_argument('--seed', type=int, default=100)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument(
        '--opponent',
        default='old',
        help='random | old | medium | mixed (по всем трём)',
    )
    parser.add_argument('--grid', default='', help='какие веса перебирать (через запятую)')
    args = parser.parse_args()

    rules = Rules()
    if args.opponent == 'mixed':
        opponents = [RandomPolicy(), LegacyPolicy(), make_policy('medium')]
    else:
        opponents = [OPPONENTS[args.opponent]()]

    def evaluate(weights: Weights) -> float:
        policy = TunablePolicy(weights)
        return sum(
            duel(policy, opponent, args.games, args.seed + index, rules)
            for index, opponent in enumerate(opponents)
        ) / len(opponents)

    grid = {
        'opp': (2.0, 3.5, 5.0, 7.0, 9.5),
        'flex': (0.0, 0.5, 1.0, 1.8, 3.0),
        'dump': (0.0, 0.1, 0.2, 0.35, 0.6),
        'dbl': (0.0, 0.4, 0.9, 1.6),
        'same': (0.0, 0.6, 1.2, 2.2),
        'dead_all': (1.0, 2.0, 3.0, 4.5),
        'dead_one': (0.0, 0.5, 1.2),
        'ctrl': (0.0, 0.3, 0.7, 1.2),
        'endgame': (-1.2, -0.6, -0.2, 0.0),
        'solver': (0, 6, 8, 10),
    }
    if args.grid:
        wanted = {part.strip() for part in args.grid.split(',')}
        grid = {key: value for key, value in grid.items() if key in wanted}

    best = Weights()
    best_score = evaluate(best)
    print(f'старт: {best_score:.3f} против {args.opponent}', flush=True)

    for round_index in range(args.rounds):
        improved = False
        for name, values in grid.items():
            for value in values:
                if value == getattr(best, name):
                    continue
                candidate = Weights(**{**asdict(best), name: value})
                started = time.perf_counter()
                score = evaluate(candidate)
                marker = ''
                if score > best_score + 1e-9:
                    best, best_score = candidate, score
                    improved = True
                    marker = '  <-- лучше'
                print(
                    f'[{round_index}] {name}={value:<5} {score:.3f} '
                    f'({time.perf_counter() - started:.1f}s){marker}',
                    flush=True,
                )
        print(f'раунд {round_index}: {best_score:.3f}', flush=True)
        if not improved:
            break

    print('\nЛучшие веса:')
    for field_ in fields(Weights):
        print(f'    {field_.name}={getattr(best, field_.name)!r},')
    print(f'Оценка: {best_score:.3f}')


if __name__ == '__main__':
    main()
