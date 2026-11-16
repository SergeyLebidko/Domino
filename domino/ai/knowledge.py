"""Знания игрока о скрытых костях."""

from __future__ import annotations

import math
from dataclasses import dataclass

from domino.engine import FULL_SET, GameState, Tile


@dataclass(frozen=True)
class Knowledge:
    """Всё, что игрок знает о скрытых костях."""

    opponent: int
    #: Все кости, которых игрок не видит (базар + рука соперника).
    unseen: tuple[Tile, ...]
    #: Кости, которые ещё могут оказаться на руке соперника.
    candidates: tuple[Tile, ...]
    #: Масти, которые у соперника гарантированно отсутствуют.
    absent: frozenset[int]
    opponent_count: int

    @classmethod
    def build(cls, state: GameState, player: int) -> 'Knowledge':
        opponent = 1 - player
        visible = set(state.hands[player]) | {slot.tile for slot in state.chain}
        unseen = tuple(tile for tile in FULL_SET if tile not in visible)
        absent = state.known_absent[opponent]
        candidates = tuple(t for t in unseen if not (t.a in absent or t.b in absent))
        return cls(
            opponent=opponent,
            unseen=unseen,
            candidates=candidates,
            absent=absent,
            opponent_count=len(state.hands[opponent]),
        )

    # -- простые счётчики ---------------------------------------------------

    def remaining(self, pip: int) -> int:
        """Сколько костей с этой мастью ещё не видны игроку."""
        return sum(1 for tile in self.unseen if tile.has(pip))

    def remaining_for_opponent(self, pip: int) -> int:
        """Сколько невидимых костей с мастью могут лежать у соперника."""
        if pip in self.absent:
            return 0
        return sum(1 for tile in self.candidates if tile.has(pip))

    @property
    def bazaar_count(self) -> int:
        return len(self.unseen) - self.opponent_count

    # -- вероятности --------------------------------------------------------

    def expected_in_hand(self, pip: int) -> float:
        """Ожидаемое число костей с мастью на руке соперника."""
        if not self.candidates or not self.opponent_count:
            return 0.0
        if pip in self.absent:
            return 0.0
        share = self.opponent_count / len(self.candidates)
        return self.remaining_for_opponent(pip) * share

    def reply_chance(self, pip: int) -> float:
        """Вероятность, что у соперника есть хотя бы одна кость с этой мастью."""
        if pip in self.absent:
            return 0.0
        pool = len(self.unseen)
        if not pool or not self.opponent_count:
            return 0.0
        matching = self.remaining(pip)
        if matching <= 0:
            return 0.0
        total = math.comb(pool, self.opponent_count)
        if total <= 0:
            return 0.0
        miss = math.comb(pool - matching, self.opponent_count)
        return 1.0 - miss / total

    def is_dead(self, pip: int) -> bool:
        """Масть, которую нечем поддержать: все кости с ней уже видны."""
        return self.remaining(pip) == 0


def pips_of(tiles) -> int:
    return sum(t.pips for t in tiles)
