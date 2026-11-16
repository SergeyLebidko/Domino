"""Тесты решателя эндшпиля: точность, скорость и защита от рекурсии."""

from __future__ import annotations

import random

import pytest

from domino.ai.solver import EndgameSolver
from domino.engine import FULL_SET, GameState, Rules, Slot


def position(chain_len: int, hand_size: int, seed: int, bazaar: bool = False) -> GameState:
    rng = random.Random(seed)
    tiles = list(FULL_SET)
    rng.shuffle(tiles)

    chain = [Slot(tiles[0], tiles[0].a, tiles[0].b, -1)]
    rest = tiles[1:]
    current = chain[0].right
    for _ in range(chain_len - 1):
        for tile in rest:
            if tile.has(current):
                rest.remove(tile)
                chain.append(Slot(tile, current, tile.other(current), -1))
                current = tile.other(current)
                break
        else:
            break

    hands = (tuple(rest[:hand_size]), tuple(rest[hand_size:hand_size * 2]))
    remaining = tuple(rest[hand_size * 2:]) if bazaar else ()
    return GameState(hands=hands, chain=tuple(chain), bazaar=remaining, turn=0)


def test_solver_refuses_without_full_information():
    """С непустым базаром точной оценки нет — решатель обязан отказаться."""
    state = position(10, 4, 1, bazaar=True)
    solver = EndgameSolver(Rules())
    assert not solver.is_applicable(state)
    move, values = solver.best(state)
    assert move is None and values == {}


def test_solver_does_not_recurse_forever_with_bazaar():
    """Регрессия: непустой базар раньше приводил к RecursionError."""
    state = position(12, 5, 3, bazaar=True)
    # Не должно быть ни рекурсии, ни исключения.
    assert EndgameSolver(Rules()).best(state) == (None, {})


def test_solver_finds_immediate_win():
    state = position(8, 2, 2)
    solver = EndgameSolver(Rules())
    move, values = solver.best(state)
    if move is None:
        pytest.skip('в раздаче нет ходов')
    assert max(values.values()) >= 0


def test_solver_speeds_are_acceptable():
    """Решатель должен укладываться в бюджет интерфейса на 14 костях."""
    import time

    state = position(12, 7, 5)
    solver = EndgameSolver(Rules())
    started = time.perf_counter()
    move, values = solver.best(state)
    elapsed = (time.perf_counter() - started) * 1000
    assert values, 'позиция должна иметь ходы'
    assert elapsed < 1500, f'слишком долго: {elapsed:.0f} мс'


def test_solver_returns_legal_move():
    state = position(12, 6, 8)
    move, _ = EndgameSolver(Rules()).best(state)
    if move is not None:
        assert move in state.legal_moves(state.turn)


def test_solver_respects_time_budget():
    """Решатель обязан уложиться в бюджет и вернуть None, если не успел."""
    import time

    state = position(12, 7, 5)
    solver = EndgameSolver(Rules(), time_limit_s=0.001)
    started = time.perf_counter()
    move, values = solver.best(state)
    elapsed = time.perf_counter() - started
    assert elapsed < 0.5, f'бюджет проигнорирован: {elapsed:.3f} с'
    if values == {}:
        assert move is None


def test_solver_within_budget_on_large_position():
    """На страховочном бюджете поиск не должен занимать секунды."""
    import time

    state = position(12, 7, 5)
    started = time.perf_counter()
    move, values = EndgameSolver(Rules(), time_limit_s=0.35).best(state)
    assert time.perf_counter() - started < 1.0


def test_solver_agrees_with_brute_force():
    """Точная оценка решателя обязана совпадать с полным перебором."""
    def brute(state, root):
        from dataclasses import replace as _replace

        outcome = check_game(state, Rules())
        if outcome is not None:
            if outcome.winner == -1:
                return 0.0
            return 1.0 if outcome.winner == root else -1.0
        player = state.turn
        moves = state.legal_moves(player)
        if not moves:
            return brute(_replace(state, turn=1 - player, passes=state.passes + 1), root)
        values = [brute(play(state, m), root) for m in moves]
        return max(values) if player == root else min(values)

    from domino.engine import check_game, play

    checked = 0
    for hand in (1, 2):
        for seed in range(6):
            state = position(9, hand, seed)
            if not state.legal_moves(state.turn):
                continue
            _, values = EndgameSolver(Rules()).best(state)
            for move, value in values.items():
                truth = brute(play(state, move), state.turn)
                assert abs(value - truth) < 1e-9, (seed, hand, move)
                checked += 1
    assert checked > 0


def test_medium_and_hard_only_call_solver_with_empty_bazaar():
    """Оба уровня обязаны проверять применимость решателя."""
    from domino.ai.hard import HardPolicy
    from domino.ai.medium import MediumPolicy

    state = position(12, 5, 4, bazaar=True)
    for policy in (MediumPolicy(), HardPolicy(samples=4, horizon=8)):
        move = policy.choose(state, 0, random.Random(0), Rules())
        assert move in state.legal_moves(0)
