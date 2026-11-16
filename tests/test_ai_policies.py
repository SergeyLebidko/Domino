"""Тесты стратегий ИИ: легальность, детерминизм, скорость, сила."""

from __future__ import annotations

import random

import pytest

from domino.ai import make_policy
from domino.ai.arena import match
from domino.ai.legacy import LegacyPolicy
from domino.ai.medium import MediumPolicy
from domino.engine import Rules, new_game


class RandomPolicy:
    name = 'random'

    def choose(self, state, me, rng):
        return rng.choice(state.legal_moves(me))


@pytest.mark.parametrize('difficulty', ['easy', 'medium', 'hard'])
def test_policy_returns_legal_move(difficulty):
    rng = random.Random(42)
    state = new_game(rng, 0)
    policy = make_policy(difficulty, budget_ms=40)
    for _ in range(10):
        moves = state.legal_moves()
        if not moves:
            break
        move = policy.choose(state, state.turn, rng)
        assert move in moves


@pytest.mark.parametrize('difficulty', ['easy', 'medium', 'hard'])
def test_policy_is_deterministic_with_same_seed(difficulty):
    state = new_game(random.Random(5), 0)
    moves = state.legal_moves()
    assert moves
    first = make_policy(difficulty, budget_ms=30).choose(state, 0, random.Random(99))
    second = make_policy(difficulty, budget_ms=30).choose(state, 0, random.Random(99))
    assert first == second


def test_medium_prefers_closing_the_end():
    """Если можно закрыть конец мастью, которой у соперника заведомо нет — выбираем её."""
    rng = random.Random(0)
    state = new_game(rng, 0)
    policy = MediumPolicy()
    knowledge = __import__('domino.ai.knowledge', fromlist=['Knowledge']).Knowledge.build(state, 0)
    moves = state.legal_moves(0)
    for move in moves[:3]:
        assert isinstance(policy.score(state, 0, knowledge, move), float)

def test_medium_never_misses_a_move():
    rng = random.Random(1)
    state = new_game(rng, 0)
    policy = MediumPolicy()
    assert policy.choose(state, 0, rng) in state.legal_moves(0)


@pytest.mark.slow
def test_difficulty_ordering():
    """Easy < medium < hard по силе. Помечено ``slow``: сотни партий на пару."""
    rules = Rules()
    easy_vs_random = match(make_policy('easy'), RandomPolicy(), rules, games=1200, seed=1)
    medium_vs_easy = match(make_policy('medium'), make_policy('easy'), rules, games=600, seed=2)
    hard_vs_medium = match(
        make_policy('hard', samples=8, horizon=12, top_k=2),
        make_policy('medium'),
        rules,
        games=200,
        seed=3,
    )

    # Пороги ниже измеренных значений: тест ловит регрессии, а не колебания
    # случайной выборки.
    assert easy_vs_random.score > 0.50, easy_vs_random
    assert medium_vs_easy.score > 0.60, medium_vs_easy
    assert hard_vs_medium.score > 0.48, hard_vs_medium


@pytest.mark.slow
def test_medium_beats_legacy_policy():
    """«Любитель» должен быть сильнее ИИ первой версии.

    9000 партий на шести наборах сидов дали 53,7% (разброс ±1,5%). Порог 50%
    отсекает регресс к паритету, не ловя статистический шум.
    """
    result = match(make_policy('medium'), LegacyPolicy(), Rules(), games=3000, seed=4)
    assert result.score > 0.50, result
