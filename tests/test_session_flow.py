"""Тесты сессии: партия не должна «зависать», ходы всегда передаются."""

from __future__ import annotations

from dataclasses import replace

from domino.engine import Rules, make_tile
from domino.ui.session import GameSession


def _stuck_state():
    """Состояние, в котором у игрока нет ходов и базар пуст."""
    from domino.engine import Slot

    # Цепочка 0:0 — у игрока только кости без нулей.
    chain = (Slot(make_tile(0, 0), 0, 0, -1),)
    return chain


def test_player_without_moves_and_empty_bazaar_passes_turn():
    session = GameSession(Rules(), difficulty='easy', first_player=0, seed=1, enable_ai=False)
    session.state = replace(
        session.state,
        chain=_stuck_state(),
        hands=((make_tile(1, 1), make_tile(2, 2)), (make_tile(3, 3),)),
        bazaar=(),
        turn=0,
    )
    assert not session.can_move(0)
    assert session.player_draw() is True
    assert session.state.turn == 1, 'ход обязан перейти сопернику'
    assert session.state.passes == 1


def test_session_passes_when_player_stuck_midgame():
    """Доигрываем партию: сессия не должна останавливаться на «нет ходов»."""
    session = GameSession(Rules(), difficulty='easy', first_player=0, seed=4, enable_ai=False)

    for _ in range(800):
        if session.is_over:
            break
        state = session.state
        if state.turn == 0:
            if session.can_move(0):
                session.play_move(session.legal_moves(0)[0])
            else:
                session.player_draw()
        else:
            moves = session.legal_moves(1)
            if moves:
                session.play_move(moves[0])
            else:
                session.draw_tile()

    assert session.is_over
    assert session.tile_count_ok


def test_ai_turn_never_hangs_without_moves():
    session = GameSession(Rules(), difficulty='easy', first_player=1, seed=2, enable_ai=True)
    session.ai_min_think = 0.0
    session.state = replace(
        session.state,
        chain=_stuck_state(),
        hands=((make_tile(1, 1),), (make_tile(2, 2), make_tile(3, 3))),
        bazaar=(),
        turn=1,
    )

    session.start_ai_turn()
    # ИИ не может ходить: сессия должна передать ход без запуска потока.
    assert not session.ai_thinking
    assert session.state.turn == 0


def test_endgame_scores_are_awarded():
    """При блокировке победитель получает очки соперника."""
    session = GameSession(Rules(), difficulty='easy', first_player=0, seed=6, enable_ai=False)
    session.state = replace(
        session.state,
        chain=_stuck_state(),
        hands=((make_tile(1, 1),), (make_tile(6, 6), make_tile(5, 5))),
        bazaar=(),
        turn=0,
    )
    session.draw_tile()
    assert session.is_over
    assert session.outcome.winner == 0
    assert session.scores[0] == 22
