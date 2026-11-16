"""Детерминизация мира и доигрывание партии — общий код для всех уровней ИИ.

Идея PIMC (perfect-information Monte Carlo) в домино: у нас нет полной
информации о руке соперника, поэтому мы разыгрываем много «правдоподобных
миров». В каждом мире рука соперника и базар заполняются случайно из ещё
невидимых костей (с учётом мастей, которые соперник уже «засветил»), а затем
партия доигрывается до конца простой политикой. Ход, который в среднем даёт
лучший результат, и выбирается.
"""

from __future__ import annotations

import random
from dataclasses import replace

from domino.ai.knowledge import Knowledge
from domino.engine import GameState, Move, Rules, check_game, draw, play

#: Качество доигрывания: чем больше горизонт, тем точнее оценка.
SHALLOW_HORIZON = 12
DEEP_HORIZON = 44


def sample_world(
    state: GameState,
    me: int,
    knowledge: Knowledge,
    rng: random.Random,
) -> GameState:
    """Согласованная раскладка: рука соперника и содержимое базара."""
    pool = list(knowledge.candidates)
    rng.shuffle(pool)
    count = knowledge.opponent_count
    opponent_hand = tuple(pool[:count])

    used = set(opponent_hand)
    bazaar = [tile for tile in knowledge.unseen if tile not in used]
    rng.shuffle(bazaar)

    hands = list(state.hands)
    hands[1 - me] = opponent_hand
    return replace(state, hands=(hands[0], hands[1]), bazaar=tuple(bazaar))


def playout(
    state: GameState,
    me: int,
    rules: Rules,
    rng: random.Random,
    horizon: int,
    policy,
) -> float:
    """Доигрывает позицию политикой ``policy`` и оценивает её с точки зрения ``me``.

    ``policy`` — объект с методом ``score(state, player, knowledge, move)``.
    Возвращает 1.0 (победа), 0.5 (ничья) или 0.0 (поражение).
    """
    for _ in range(horizon):
        outcome = check_game(state, rules)
        if outcome is not None:
            return _value(outcome.winner, me)

        player = state.turn
        moves = state.legal_moves(player)
        if not moves:
            if not state.bazaar:
                outcome = check_game(state, rules)
                if outcome is not None:
                    return _value(outcome.winner, me)
                # Оба не могут ходить — дальше решать нечего.
                return 0.5

            state, _ = draw(state, rules)
            if state.turn == player:
                # Добор не помог: передаём ход, чтобы не зациклиться.
                state = replace(state, turn=1 - player, passes=state.passes + 1)
            continue

        state = play(state, _greedy(state, player, moves, policy, rng))

    mine, theirs = state.pips_of(me), state.pips_of(1 - me)
    if mine < theirs:
        return 0.7
    if mine > theirs:
        return 0.3
    return 0.5


def _greedy(state: GameState, player: int, moves: list[Move], policy, rng: random.Random) -> Move:
    if len(moves) == 1:
        return moves[0]
    knowledge = Knowledge.build(state, player)
    scored = [(policy.score(state, player, knowledge, move), move) for move in moves]
    best = max(value for value, _ in scored)
    return rng.choice([move for value, move in scored if value >= best - 1e-9])


def _value(winner: int, me: int) -> float:
    if winner < 0:
        return 0.5
    return 1.0 if winner == me else 0.0


def pimc_choose(
    state: GameState,
    me: int,
    rng: random.Random,
    rules: Rules,
    *,
    policy,
    static_scores: dict[Move, float],
    samples: int,
    horizon: int,
    top_k: int,
    static_weight: float = 0.5,
    min_samples: int = 1,
    deadline: float | None = None,
) -> tuple[Move, list[float], int]:
    """Оценивает ходы по мирам и возвращает лучший.

    ``static_scores`` используются и для обрезки корневых ходов, и как
    «априорная» добавка к оценке (уменьшает дисперсию при малом числе миров).
    """
    moves = state.legal_moves(me)
    if not moves:
        raise ValueError('Нет легальных ходов')
    if len(moves) == 1:
        return moves[0], [1.0], 0

    ranked = sorted(moves, key=lambda m: static_scores[m], reverse=True)
    candidates = ranked[: max(1, top_k)]
    if len(candidates) == 1:
        return candidates[0], [1.0], 0

    knowledge = Knowledge.build(state, me)
    totals = [0.0] * len(candidates)
    done = 0

    while done < samples:
        if done >= min_samples and deadline is not None:
            import time

            if time.perf_counter() >= deadline:
                break
        world = sample_world(state, me, knowledge, rng)
        for index, move in enumerate(candidates):
            totals[index] += playout(play(world, move), me, rules, rng, horizon, policy)
        done += 1

    if not done:
        return candidates[0], [0.0] * len(candidates), 0

    span = (max(static_scores.values()) - min(static_scores.values())) or 1.0
    values = [
        totals[index] / done + static_weight * static_scores[move] / span
        for index, move in enumerate(candidates)
    ]
    best = max(range(len(candidates)), key=lambda i: values[i])
    return candidates[best], values, done
