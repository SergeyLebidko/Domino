"""Поиск формулы оценки хода: legacy-признаки + вероятностные.

Запуск: ``python3 -m tools.search``

Сравнение парное (общие раздачи), поэтому шум небольшой и можно перебрать
десятки вариантов за минуты. Результат — лучший набор весов, который затем
вручную переносится в ``domino/ai/medium.py``.
"""

from __future__ import annotations

import argparse
import math
import random
import time
from dataclasses import asdict, dataclass, fields
from itertools import count

from domino.ai.legacy import LegacyPolicy
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

FEATURES = (
    'opp',        # -P(ответ) по каждому концу
    'k',          # -ожидаемое число подходящих костей у соперника
    'chain_l',    # +костей в цепочке с левым концом
    'chain_r',
    'own_l',      # +своих костей с левым концом
    'own_r',
    'dbl',        # +дубль
    'dbl_suit',   # +дубль, масть которого уже вышла
    'pips',       # +очки кости
    'same',       # +концы совпали
    'dead_l',     # +соперник не может ответить на левый конец
    'dead_r',
    'dead_all',   # +ни на один
    'flex',       # +своих костей к новым концам
    'tight',      # -мёртвые кости на руке в эндшпиле
)


@dataclass
class W:
    opp: float = 0.0
    k: float = 0.0
    chain_l: float = 0.0
    chain_r: float = 0.0
    own_l: float = 0.0
    own_r: float = 0.0
    dbl: float = 0.0
    dbl_suit: float = 0.0
    pips: float = 0.0
    same: float = 0.0
    dead_l: float = 0.0
    dead_r: float = 0.0
    dead_all: float = 0.0
    flex: float = 0.0
    tight: float = 0.0


LEGACY = W(chain_l=1, chain_r=1, own_l=1, own_r=1, dbl_suit=1)
PROB = W(opp=9.5, pips=0.2, dbl=1.6, same=2.2, dead_all=1.0, dead_l=1.2, dead_r=1.2,
         tight=-0.6)
MIXED = W(opp=4.0, chain_l=0.7, chain_r=0.7, own_l=0.7, own_r=0.7, dbl_suit=0.4,
          pips=0.15, same=1.2, dead_l=0.8, dead_r=0.8, dead_all=1.5, flex=0.4,
          tight=-0.4)


class Policy:
    name = 'search'

    def __init__(self, weights: W) -> None:
        self.w = weights
        self.rules = Rules()

    def choose(self, state: GameState, me: int, rng: random.Random, rules=None):
        moves = state.legal_moves(me)
        if len(moves) == 1:
            return moves[0]
        unseen = self._unseen(state, me)
        scored = [(self._score(state, me, move, unseen), move) for move in moves]
        best = max(value for value, _ in scored)
        return rng.choice([move for value, move in scored if value >= best - 1e-9])

    @staticmethod
    def _unseen(state: GameState, me: int):
        visible = set(state.hands[me]) | {slot.tile for slot in state.chain}
        return [tile for tile in FULL_SET if tile not in visible]

    def _score(self, state: GameState, me: int, move, unseen) -> float:
        w = self.w
        tile = move.tile
        left, right = ends_after(state.left_end, state.right_end, move)
        rest = [t for t in state.hands[me] if t != tile]
        opponent_size = len(state.hands[1 - me])
        pool = len(unseen)

        def matching(pip):
            return sum(1 for t in unseen if t.has(pip))

        def chance(pip):
            k = matching(pip)
            if k <= 0 or not pool or not opponent_size:
                return 0.0
            return 1.0 - math.comb(pool - k, opponent_size) / math.comb(pool, opponent_size)

        def expected(pip):
            if not pool or not opponent_size:
                return 0.0
            return matching(pip) * opponent_size / pool

        chain = state.chain
        score = 0.0
        score -= w.opp * (chance(left) + chance(right))
        score -= w.k * (expected(left) + expected(right))
        score += w.chain_l * sum(1 for s in chain if s.tile.has(left))
        score += w.chain_r * sum(1 for s in chain if s.tile.has(right))
        score += w.own_l * sum(1 for t in rest if t.has(left))
        score += w.own_r * sum(1 for t in rest if t.has(right))
        if tile.is_double:
            score += w.dbl
            score += w.dbl_suit * sum(1 for s in chain if s.tile.has(tile.a))
        score += w.pips * tile.pips
        if left == right:
            score += w.same
        if chance(left) == 0:
            score += w.dead_l
        if chance(right) == 0:
            score += w.dead_r
        if chance(left) == 0 and chance(right) == 0:
            score += w.dead_all
        score += w.flex * sum(1 for t in rest if t.has(left) or t.has(right))
        if len(rest) <= 3:
            score += w.tight * sum(1 for t in rest if not t.has(left) and not t.has(right))
        return score


def duel(policy, opponent, games: int, seed: int, rules: Rules) -> float:
    wins = losses = draws = 0
    for index in range(games):
        rng = random.Random(seed * 1_000_003 + index)
        state = new_game(rng, index % 2)
        winner = -1
        for _ in range(600):
            outcome = check_game(state, rules)
            if outcome is not None:
                winner = outcome.winner
                break
            if not state.legal_moves():
                state, _ = draw(state, rules)
                continue
            chooser = policy if state.turn == 0 else opponent
            state = play(state, chooser.choose(state, state.turn, rng, rules))
        if winner == 0:
            wins += 1
        elif winner == 1:
            losses += 1
        else:
            draws += 1
    return (wins + 0.5 * draws) / games


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--games', type=int, default=1200)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--iterations', type=int, default=60)
    args = parser.parse_args()

    rules = Rules()
    opponents = [LegacyPolicy()]

    def evaluate(weights: W) -> float:
        policy = Policy(weights)
        return sum(
            duel(policy, opponent, args.games, args.seed + index, rules)
            for index, opponent in enumerate(opponents)
        ) / len(opponents)

    starts = {'legacy': LEGACY, 'prob': PROB, 'mixed': MIXED}
    best = None
    best_score = -1.0
    for name, weights in starts.items():
        started = time.perf_counter()
        score = evaluate(weights)
        print(f'старт {name:<7} {score:.3f} ({time.perf_counter() - started:.1f}s)', flush=True)
        if score > best_score:
            best, best_score = weights, score

    rng = random.Random(1234)
    scale = 1.5
    for iteration in count(1):
        if iteration > args.iterations:
            break
        candidate = asdict(best)
        for field_ in fields(W):
            if rng.random() < 0.5:
                candidate[field_.name] = max(
                    -12.0, min(12.0, candidate[field_.name] + rng.gauss(0, scale))
                )
        weights = W(**candidate)
        score = evaluate(weights)
        if score > best_score:
            best, best_score = weights, score
            print(f'[{iteration}] {score:.3f}  {asdict(best)}', flush=True)
        elif iteration % 10 == 0:
            print(f'[{iteration}] нет улучшения (лучший {best_score:.3f})', flush=True)
            scale = max(0.3, scale * 0.85)

    print(f'\nЛучший результат: {best_score:.3f}')
    print(asdict(best))


if __name__ == '__main__':
    main()
