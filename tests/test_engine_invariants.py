"""Инварианты движка: их нарушение ломает и игру, и симуляции ИИ."""

from __future__ import annotations

import random

import pytest

from domino.ai import make_policy
from domino.engine import (
    FULL_SET,
    Rules,
    check_game,
    draw,
    new_game,
    pips,
    play,
)


def all_tiles(state):
    tiles = list(state.hands[0]) + list(state.hands[1]) + list(state.bazaar)
    tiles += [slot.tile for slot in state.chain]
    return tiles


@pytest.mark.parametrize('seed', range(5))
def test_tile_conservation(seed):
    rules = Rules()
    rng = random.Random(seed)
    state = new_game(rng, seed % 2)
    policies = (make_policy('medium'), make_policy('medium'))

    for _ in range(300):
        assert len(all_tiles(state)) == 28
        assert sorted(all_tiles(state)) == sorted(FULL_SET)
        if check_game(state, rules):
            break
        if not state.legal_moves():
            state, _ = draw(state, rules)
            continue
        state = play(state, policies[state.turn].choose(state, state.turn, rng))


@pytest.mark.parametrize('seed', range(5))
def test_chain_stays_consistent(seed):
    rng = random.Random(seed)
    state = new_game(rng, 0)
    policies = (make_policy('easy'), make_policy('easy'))

    for _ in range(200):
        for previous, current in zip(state.chain, state.chain[1:]):
            assert previous.right == current.left
        moves = state.legal_moves()
        if not moves:
            state, _ = draw(state, Rules())
            continue
        state = play(state, policies[state.turn].choose(state, state.turn, rng))


def test_pips_are_non_increasing_while_playing():
    rng = random.Random(11)
    state = new_game(rng, 0)
    previous_total = pips(state.hands[0]) + pips(state.hands[1])

    for _ in range(60):
        if not state.legal_moves():
            break
        state = play(state, state.legal_moves()[0])
        total = pips(state.hands[0]) + pips(state.hands[1])
        assert total <= previous_total
        previous_total = total


def test_game_always_terminates():
    """Партия обязана завершаться: базар не бесконечен, пасы ограничены."""
    rules = Rules()
    for seed in range(30):
        rng = random.Random(seed)
        state = new_game(rng, 0)
        policies = (make_policy('easy'), make_policy('easy'))
        finished = False
        for _ in range(400):
            if check_game(state, rules):
                finished = True
                break
            if not state.legal_moves():
                state, _ = draw(state, rules)
                continue
            state = play(state, policies[state.turn].choose(state, state.turn, rng))
        assert finished, f'партия {seed} не завершилась'
