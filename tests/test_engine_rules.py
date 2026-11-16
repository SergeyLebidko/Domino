"""Тесты правил движка."""

from __future__ import annotations

import random

import pytest

from domino.engine import (
    FULL_SET,
    LEFT,
    RIGHT,
    GameState,
    Move,
    Rules,
    Slot,
    Tile,
    blocked_outcome,
    check_game,
    draw,
    ends_after,
    legal_moves,
    make_tile,
    new_game,
    pass_turn,
    pips,
    play,
)


def state_with(chain, hands, bazaar=(), turn=0) -> GameState:
    return GameState(hands=hands, chain=tuple(chain), bazaar=tuple(bazaar), turn=turn)


def slot(a, b, left=None, right=None, owner=-1) -> Slot:
    tile = make_tile(a, b)
    return Slot(tile, tile.a if left is None else left, tile.b if right is None else right, owner)


def test_full_set_has_28_unique_tiles():
    assert len(FULL_SET) == 28
    assert len(set(FULL_SET)) == 28
    assert all(t.a <= t.b for t in FULL_SET)


def test_make_tile_normalizes_order():
    assert make_tile(4, 2) == Tile(2, 4)


def test_new_game_deals_correctly():
    state = new_game(random.Random(7))
    assert len(state.hands[0]) == 7
    assert len(state.hands[1]) == 7
    assert len(state.bazaar) == 13
    assert len(state.chain) == 1
    everything = list(state.hands[0]) + list(state.hands[1]) + list(state.bazaar) + [state.chain[0].tile]
    assert sorted(everything) == sorted(FULL_SET)


def test_chain_ends_are_consistent():
    state = new_game(random.Random(3))
    for _ in range(30):
        moves = state.legal_moves()
        if not moves:
            break
        move = moves[0]
        state = play(state, move)
        for previous, current in zip(state.chain, state.chain[1:]):
            assert previous.right == current.left


def test_legal_moves_respect_both_ends():
    hand = (Tile(3, 6), Tile(2, 2), Tile(5, 1))
    moves = legal_moves(hand, left=3, right=5)
    assert Move(Tile(3, 6), LEFT) in moves
    assert Move(Tile(5, 1), RIGHT) in moves
    assert all(m.tile != Tile(2, 2) for m in moves)


def test_play_left_updates_chain_and_hand():
    chain = [slot(3, 5)]
    state = state_with(chain, ((Tile(3, 6),), ()))
    new_state = play(state, Move(Tile(3, 6), LEFT))
    assert new_state.chain[0].left == 6
    assert new_state.chain[0].right == 3
    assert new_state.left_end == 6
    assert new_state.right_end == 5
    assert new_state.hands[0] == ()
    assert new_state.turn == 1


def test_play_right_updates_chain():
    chain = [slot(3, 5)]
    state = state_with(chain, ((Tile(5, 5),), ()))
    new_state = play(state, Move(Tile(5, 5), RIGHT))
    assert new_state.right_end == 5
    assert new_state.chain[-1].left == 5
    assert new_state.chain[-1].right == 5


def test_play_rejects_illegal_tile():
    state = state_with([slot(3, 5)], ((Tile(1, 1),), ()))
    with pytest.raises(ValueError):
        play(state, Move(Tile(1, 1), LEFT))


def test_play_rejects_tile_not_in_hand():
    state = state_with([slot(3, 5)], ((Tile(5, 5),), ()))
    with pytest.raises(ValueError):
        play(state, Move(Tile(3, 6), RIGHT))


def test_play_is_immutable():
    chain = [slot(3, 5)]
    state = state_with(chain, ((Tile(3, 6), Tile(1, 1)), (Tile(2, 2),)))
    before = (state.chain, state.hands, state.turn)
    play(state, Move(Tile(3, 6), LEFT))
    assert (state.chain, state.hands, state.turn) == before


def test_ends_after():
    assert ends_after(3, 5, Move(Tile(3, 6), LEFT)) == (6, 5)
    assert ends_after(3, 5, Move(Tile(5, 0), RIGHT)) == (3, 0)


def test_draw_until_playable():
    # На руке нет троек, в базаре играбельная кость лежит глубже.
    chain = [slot(3, 4)]
    hands = ((Tile(0, 1),), ())
    bazaar = (Tile(2, 2), Tile(3, 3), Tile(5, 6))
    state = state_with(chain, hands, bazaar)
    new_state, drawn = draw(state, Rules(draw_until_playable=True))
    assert Tile(3, 3) in new_state.hands[0]
    assert len(drawn) == 2
    assert new_state.turn == 0  # ход остался у игрока: он теперь может играть
    assert new_state.can_move(0)


def test_draw_one_at_a_time_when_disabled():
    chain = [slot(3, 4)]
    # Верхняя кость базара не играбельна: при выключенном правиле берём ровно одну.
    state = state_with(chain, ((Tile(0, 1),), ()), (Tile(3, 3), Tile(2, 2)))
    new_state, drawn = draw(state, Rules(draw_until_playable=False))
    assert len(drawn) == 1
    assert new_state.turn == 1  # играбельной кости нет, ход передан


def test_draw_passes_when_bazaar_empty_and_blocked():
    chain = [slot(3, 4)]
    state = state_with(chain, ((Tile(0, 1),), (Tile(2, 2),)), ())
    new_state, drawn = draw(state, Rules())
    assert drawn == ()
    assert new_state.turn == 1


def test_draw_records_end_pips_as_absent():
    chain = [slot(3, 4)]
    state = state_with(chain, ((Tile(0, 1),), ()), (Tile(2, 2),))
    new_state, _ = draw(state, Rules())
    assert new_state.known_absent[0] == frozenset({3, 4})


def test_absent_cleared_for_played_pip():
    chain = [slot(3, 4)]
    state = state_with(chain, ((Tile(3, 6),), ()), ())
    state = state.with_absent(0, frozenset({3, 4}))
    assert state.known_absent[0]
    state = play(state, Move(Tile(3, 6), LEFT))
    # Масть 3 сыграна, значит она у нас есть; масть 4 по-прежнему отсутствует.
    assert state.known_absent[0] == frozenset({4})


def test_check_game_win_on_empty_hand():
    rules = Rules()
    chain = [slot(3, 4)]
    state = state_with(chain, ((), (Tile(6, 6),)))
    outcome = check_game(state, rules)
    assert outcome is not None
    assert outcome.winner == 0
    assert outcome.reason == 'empty_hand'
    assert outcome.points == 12


def test_blocked_game_compares_pips():
    rules = Rules(pips_on_blocked=True)
    chain = [slot(3, 4)]
    state = state_with(chain, ((Tile(0, 1),), (Tile(6, 6),)))
    assert state.is_blocked
    outcome = check_game(state, rules)
    assert outcome is not None
    assert outcome.winner == 0
    assert outcome.points == 12


def test_blocked_game_draw_on_equal_pips():
    rules = Rules(pips_on_blocked=True)
    chain = [slot(3, 4)]
    state = state_with(chain, ((Tile(1, 1),), (Tile(0, 2),)))
    outcome = blocked_outcome(state, rules)
    assert outcome.winner == -1


def test_blocked_as_draw_when_disabled():
    rules = Rules(pips_on_blocked=False)
    chain = [slot(3, 4)]
    state = state_with(chain, ((Tile(0, 1),), (Tile(6, 6),)))
    outcome = check_game(state, rules)
    assert outcome is not None
    assert outcome.winner == -1


def test_pips():
    assert pips([Tile(1, 2), Tile(6, 6)]) == 15


def test_pass_turn_increments_counter():
    state = state_with([slot(3, 4)], ((Tile(0, 1),), (Tile(0, 2),)))
    passed = pass_turn(state)
    assert passed.turn == 1
    assert passed.passes == 1
