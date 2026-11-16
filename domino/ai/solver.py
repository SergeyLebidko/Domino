"""Точный решатель эндшпиля.

Когда базар пуст, оба игрока знают все кости (своя рука видна, а остальные
выводятся однозначно). Тогда игра с полной информацией решается минимаксом с
альфа-бета отсечением: ветвление маленькое (≤14 ходов), поэтому поиск до конца
партии занимает миллисекунды.

Решатель намеренно работает только при пустом базаре. Если базар не пуст,
информации недостаточно, и вызывать его нельзя — иначе пропуск хода с
возможным добором превращается в бесконечную рекурсию.
"""

from __future__ import annotations

from dataclasses import replace

from domino.engine import GameState, Rules, check_game, play

#: Оценки с точки зрения игрока, чей ход.
WIN = 1.0
LOSE = -1.0
DRAW = 0.0

#: Защита от патологических позиций: глубина в полуходах.
MAX_DEPTH = 64


class SolverTimeout(Exception):
    """Поиск прерван из-за исчерпания бюджета."""


class EndgameSolver:
    """Минимакс с мемоизацией для позиций без базара."""

    def __init__(self, rules: Rules, node_limit: int | None = None,
                 time_limit_s: float | None = None) -> None:
        self.rules = rules
        self.nodes = 0
        self.node_limit = node_limit
        self.time_limit_s = time_limit_s
        self._deadline: float | None = None

    def is_applicable(self, state: GameState) -> bool:
        """Решатель применим только при полной информации."""
        return not state.bazaar

    def solve(self, state: GameState) -> dict:
        """Оценка каждого хода игрока, чей сейчас ход: {move: value}."""
        self.nodes = 0
        self._table: dict = {}
        if self.time_limit_s:
            import time

            self._deadline = time.perf_counter() + self.time_limit_s
        else:
            self._deadline = None

        player = state.turn
        results: dict = {}
        for move in state.legal_moves(player):
            child = play(state, move)
            results[move] = self._search(child, player, LOSE - 1, WIN + 1, depth=1)
        return results

    def best(self, state: GameState) -> tuple[object, dict]:
        """Лучший ход и оценки всех ходов. Пустой результат — решать нечего.

        Если поиск прерван по бюджету, возвращается ``(None, {})``: решение
        остаётся за вызывающей стратегией.
        """
        if not self.is_applicable(state):
            return None, {}
        try:
            results = self.solve(state)
        except SolverTimeout:
            return None, {}
        if not results:
            return None, results
        move = max(results, key=lambda m: (results[m], -m.tile.pips))
        return move, results

    # -- поиск --------------------------------------------------------------

    def _check_budget(self) -> None:
        if self.node_limit is not None and self.nodes > self.node_limit:
            raise SolverTimeout
        if self._deadline is not None:
            import time

            if time.perf_counter() > self._deadline:
                raise SolverTimeout

    def _search(
        self,
        state: GameState,
        root: int,
        alpha: float,
        beta: float,
        depth: int,
    ) -> float:
        self.nodes += 1
        self._check_budget()
        outcome = check_game(state, self.rules)
        if outcome is not None:
            if outcome.winner == -1:
                return DRAW
            return WIN if outcome.winner == root else LOSE

        key = (state.hands, state.chain, state.turn, state.passes)
        cached = self._table.get(key)
        if cached is not None:
            return cached

        player = state.turn
        moves = state.legal_moves(player)

        if not moves:
            if state.bazaar:
                # Добор: состояние зависит от случайной кости, точной оценки
                # нет. Такие позиции решатель не оценивает — вызывающий код
                # обязан проверять ``is_applicable``.
                return DRAW
            if depth > MAX_DEPTH:
                return DRAW
            # Базар пуст: пропуск хода. Второй пас подряд означает блокировку,
            # но её отловит check_game на следующем шаге.
            passed = replace(state, turn=1 - player, passes=state.passes + 1)
            value = self._search(passed, root, alpha, beta, depth + 1)
            self._table[key] = value
            return value

        maximizing = player == root
        best = LOSE - 1 if maximizing else WIN + 1
        ordered = sorted(moves, key=lambda m: -m.tile.pips)

        cutoff = False

        for move in ordered:
            child = play(state, move)
            value = self._search(child, root, alpha, beta, depth + 1)
            if maximizing:
                if value > best:
                    best = value
                if best > alpha:
                    alpha = best
            else:
                if value < best:
                    best = value
                if best < beta:
                    beta = best
            if alpha >= beta:
                cutoff = True
                break

        # Кэшируем только точные оценки: после отсечения значение является
        # лишь границей, и переиспользовать его нельзя.
        if not cutoff:
            self._table[key] = best
        return best
