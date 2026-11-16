"""Бенчмарк ИИ: ``python3 -m tools.arena``."""

from __future__ import annotations

import argparse
import random
import time

from domino.ai import make_policy
from domino.ai.arena import Result, play_game
from domino.engine import Rules


class RandomPolicy:
    name = 'random'

    def choose(self, state, me, rng):
        return rng.choice(state.legal_moves(me))


def run(pairs, games: int, seed: int, rules: Rules) -> None:
    for left, right in pairs:
        started = time.perf_counter()
        result = Result()
        for index in range(games):
            rng = random.Random(seed * 1_000_003 + index)
            first = index % 2
            winner = play_game((left, right), rules, rng, first)
            result.add(winner)
        elapsed = time.perf_counter() - started
        print(
            f'{left.name:>7} vs {right.name:<7} {result} '
            f'[{elapsed:5.1f}s, {elapsed / max(1, games) * 1000:4.0f} ms/партия]'
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--games', type=int, default=200)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument(
        '--pairs',
        default='easy:random,medium:easy,medium:old,hard:medium,hard:random',
        help='пары стратегий вида a:b через запятую',
    )
    parser.add_argument('--budget', type=int, default=0,
                        help='ограничение по времени для hard, мс (0 — без ограничения)')
    parser.add_argument('--samples', type=int, default=48,
                        help='число миров для hard')
    args = parser.parse_args()

    rules = Rules()
    from domino.ai.legacy import LegacyPolicy

    cache: dict[str, object] = {}

    def pick(name: str):
        if name not in cache:
            if name == 'random':
                cache[name] = RandomPolicy()
            elif name == 'old':
                cache[name] = LegacyPolicy()
            elif name == 'hard':
                cache[name] = make_policy('hard', samples=args.samples, **(
                    {'time_guard_ms': args.budget} if args.budget else {}
                ))
            else:
                cache[name] = make_policy(name)
        return cache[name]

    pairs = []
    for spec in args.pairs.split(','):
        left_name, right_name = spec.split(':')
        pairs.append((pick(left_name), pick(right_name)))

    run(pairs, args.games, args.seed, rules)


if __name__ == '__main__':
    main()
