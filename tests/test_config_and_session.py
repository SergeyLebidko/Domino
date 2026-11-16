"""Тесты конфига, решателя эндшпиля и сессии."""

from __future__ import annotations

import json
import random

from domino.ai.solver import EndgameSolver
from domino.config import Config
from domino.engine import Rules, make_tile, new_game
from domino.ui.session import GameSession


def test_config_roundtrip(tmp_path):
    path = tmp_path / 'settings.json'
    Config(theme='club_green', difficulty='hard', first_player=1).save(path)
    loaded = Config.load(path)
    assert (loaded.theme, loaded.difficulty, loaded.first_player) == ('club_green', 'hard', 1)


def test_config_default_path_is_inside_game_dir():
    """Настройки обязаны лежать в папке игры, а не в профиле пользователя."""
    from domino.config import CONFIG_PATH, GAME_DIR

    assert CONFIG_PATH.parent == GAME_DIR
    assert CONFIG_PATH.name == 'settings.json'
    assert '.config' not in str(CONFIG_PATH)


def test_config_save_does_not_create_foreign_dirs(tmp_path):
    """Запись настроек не должна создавать каталоги вне папки игры."""
    path = tmp_path / 'nested' / 'settings.json'
    assert Config().save(path)
    assert path.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['nested']


def test_config_save_is_atomic(tmp_path):
    path = tmp_path / 'settings.json'
    assert Config().save(path)
    assert not (tmp_path / 'settings.json.tmp').exists()


def test_config_ignores_broken_file(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('{не json', encoding='utf-8')
    loaded = Config.load(path)
    assert loaded.theme == 'flat_dark'


def test_config_ignores_wrong_json_type(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('[1, 2, 3]', encoding='utf-8')
    assert Config.load(path).theme == 'flat_dark'


def test_config_validates_values(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text(json.dumps({'theme': 'neon', 'difficulty': 'insane', 'first_player': 7}))
    loaded = Config.load(path)
    assert loaded.theme == 'flat_dark'
    assert loaded.difficulty == 'medium'
    assert loaded.first_player == 0


def test_endgame_solver_finds_winning_move():
    """Последняя кость игрока гарантирует победу — решатель обязан её найти."""
    rules = Rules()
    base = new_game(random.Random(1), 0)
    from dataclasses import replace

    chain = base.chain
    left = chain[0].left
    # Рука игрока: одна кость, подходящая к левому концу.
    tile = make_tile(left, (left + 1) % 7 if left != (left + 1) % 7 else (left + 2) % 7)
    state = replace(
        base,
        hands=((tile,), (make_tile(6, 6),)),
        bazaar=(),
        turn=0,
    )
    solver = EndgameSolver(rules)
    move, results = solver.best(state)
    assert move is not None
    assert results[move] > 0


def test_session_draw_until_playable():
    session = GameSession(Rules(), difficulty='easy', first_player=0, seed=3, enable_ai=False)
    # Прокручиваем, пока не найдём момент без ходов при непустом базаре.
    for _ in range(200):
        if session.is_over:
            break
        moves = session.legal_moves(session.state.turn)
        if not moves and session.state.bazaar:
            before = len(session.state.hands[session.state.turn])
            session.draw_tile()
            assert len(session.state.hands[session.state.turn]) >= before + 1
            if session.can_move(session.state.turn):
                break
            continue
        if moves:
            session.play_move(moves[0])
    assert session.tile_count_ok


def test_session_scores_accumulate():
    session = GameSession(Rules(), difficulty='easy', first_player=0, seed=11, enable_ai=False)
    session.scores = [5, 3]
    session.restart()
    assert session.scores == [5, 3]


def test_tile_count_invariant_during_session():
    session = GameSession(Rules(), difficulty='medium', first_player=0, seed=8, enable_ai=False)
    for _ in range(150):
        assert session.total_tiles() == 28
        if session.is_over:
            break
        moves = session.legal_moves(session.state.turn)
        if not moves:
            session.draw_tile()
            continue
        session.play_move(moves[0])
