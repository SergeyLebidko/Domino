"""Чистые правила домино.

Модуль не зависит от pygame: его можно использовать в тестах, в симуляциях ИИ
и в бенчмарках. Вся партия хранится в неизменяемом ``GameState`` — любое
действие возвращает новое состояние, поэтому состояние легко клонировать,
сравнивать и перебирать.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple, Sequence

MAX_PIP = 6

LEFT = 'left'
RIGHT = 'right'


class Tile(NamedTuple):
    """Кость домино. Инвариант: ``a <= b``."""

    a: int
    b: int

    @property
    def pips(self) -> int:
        return self.a + self.b

    @property
    def is_double(self) -> bool:
        return self.a == self.b

    def has(self, pip: int) -> bool:
        return pip == self.a or pip == self.b

    def other(self, pip: int) -> int:
        """Вторая половина кости, если первая равна ``pip``."""
        return self.b if pip == self.a else self.a

    def __str__(self) -> str:
        return f'[{self.a}:{self.b}]'


def make_tile(a: int, b: int) -> Tile:
    return Tile(a, b) if a <= b else Tile(b, a)


#: Полный набор из 28 костей.
FULL_SET: tuple[Tile, ...] = tuple(
    make_tile(a, b) for a in range(MAX_PIP + 1) for b in range(a, MAX_PIP + 1)
)


class Slot(NamedTuple):
    """Кость в цепочке. ``left``/``right`` — половинки в порядке слева направо."""

    tile: Tile
    left: int
    right: int
    owner: int  # 0 — человек, 1 — ИИ, -1 — стартовая кость

    @property
    def is_double(self) -> bool:
        return self.tile.is_double


class Move(NamedTuple):
    tile: Tile
    side: str

    def __str__(self) -> str:
        return f'{self.tile} {"влево" if self.side == LEFT else "вправо"}'


@dataclass(frozen=True)
class Rules:
    """Настройки правил, которые влияют на движок."""

    #: Добирать кости, пока не появится играбельная, а не по одной за ход.
    draw_until_playable: bool = True
    #: При обоюдной блокировке побеждает тот, у кого меньше очков на руках.
    pips_on_blocked: bool = True
    #: Матч до N очков (None — каждая партия самостоятельна).
    match_target: int | None = None


class Outcome(NamedTuple):
    winner: int  # 0 — человек, 1 — ИИ, -1 — ничья
    reason: str  # 'empty_hand' | 'blocked'
    points: int


def pips(hand: Iterable[Tile]) -> int:
    return sum(tile.pips for tile in hand)


def legal_moves(hand: Sequence[Tile], left: int, right: int) -> list[Move]:
    """Все допустимые ходы для руки при текущих концах цепочки."""
    moves: list[Move] = []
    for tile in hand:
        if tile.has(left):
            moves.append(Move(tile, LEFT))
        if tile.has(right):
            moves.append(Move(tile, RIGHT))
    return moves


def has_move(hand: Sequence[Tile], left: int, right: int) -> bool:
    return any(tile.has(left) or tile.has(right) for tile in hand)


def ends_after(left: int, right: int, move: Move) -> tuple[int, int]:
    """Концы цепочки после хода (без изменения состояния)."""
    tile = move.tile
    if move.side == LEFT:
        return tile.other(left), right
    return left, tile.other(right)


@dataclass(frozen=True)
class GameState:
    hands: tuple[tuple[Tile, ...], tuple[Tile, ...]]
    chain: tuple[Slot, ...]
    bazaar: tuple[Tile, ...]
    turn: int = 0
    passes: int = 0
    drawn: tuple[int, int] = (0, 0)
    #: Масти, про которые достоверно известно, что их нет на руке игрока.
    known_absent: tuple[frozenset[int], frozenset[int]] = (frozenset(), frozenset())

    # -- доступ к состоянию -------------------------------------------------

    @property
    def left_end(self) -> int:
        return self.chain[0].left

    @property
    def right_end(self) -> int:
        return self.chain[-1].right

    def hand(self, player: int) -> tuple[Tile, ...]:
        return self.hands[player]

    def pips_of(self, player: int) -> int:
        return pips(self.hands[player])

    def legal_moves(self, player: int | None = None) -> list[Move]:
        player = self.turn if player is None else player
        return legal_moves(self.hands[player], self.left_end, self.right_end)

    @property
    def legal(self) -> list[Move]:
        return self.legal_moves()

    def can_move(self, player: int) -> bool:
        return has_move(self.hands[player], self.left_end, self.right_end)

    @property
    def bazaar_count(self) -> int:
        return len(self.bazaar)

    @property
    def is_blocked(self) -> bool:
        """Ни у кого нет ходов и базар пуст."""
        return (
            not self.bazaar
            and not self.can_move(0)
            and not self.can_move(1)
        )

    # -- действия -----------------------------------------------------------

    def with_hand(self, player: int, hand: Sequence[Tile]) -> GameState:
        hands = list(self.hands)
        hands[player] = tuple(hand)
        return replace(self, hands=(hands[0], hands[1]))

    def with_absent(self, player: int, absent: frozenset[int]) -> GameState:
        known = list(self.known_absent)
        known[player] = absent
        return replace(self, known_absent=(known[0], known[1]))


def unseen_tiles(state: GameState, player: int) -> tuple[Tile, ...]:
    """Кости, которых игрок не видит: базар + рука соперника."""
    visible = set(state.hands[player]) | {slot.tile for slot in state.chain}
    return tuple(tile for tile in FULL_SET if tile not in visible)


def new_game(rng: random.Random, first_player: int = 0) -> GameState:
    """Раздаёт новую партию: по 7 костей и стартовую кость в цепочку."""
    deck = list(FULL_SET)
    rng.shuffle(deck)

    hands = (tuple(deck[:7]), tuple(deck[7:14]))
    bazaar = tuple(deck[15:])

    opening = deck[14]
    if opening.is_double or rng.random() < 0.5:
        slot = Slot(opening, opening.a, opening.b, -1)
    else:
        slot = Slot(opening, opening.b, opening.a, -1)

    return GameState(
        hands=hands,
        chain=(slot,),
        bazaar=bazaar,
        turn=first_player % 2,
    )


def play(state: GameState, move: Move) -> GameState:
    """Кладёт кость из руки текущего игрока в цепочку."""
    player = state.turn
    hand = list(state.hands[player])

    if move.tile not in hand:
        raise ValueError(f'Кости {move.tile} нет на руке игрока {player}')

    left, right = state.left_end, state.right_end
    tile = move.tile

    if move.side == LEFT:
        if not tile.has(left):
            raise ValueError(f'Кость {tile} не подходит к левому концу {left}')
        slot = Slot(tile, tile.other(left), left, player)
        chain = (slot,) + state.chain
    elif move.side == RIGHT:
        if not tile.has(right):
            raise ValueError(f'Кость {tile} не подходит к правому концу {right}')
        slot = Slot(tile, right, tile.other(right), player)
        chain = state.chain + (slot,)
    else:
        raise ValueError(f'Неизвестное направление: {move.side!r}')

    hand.remove(tile)
    absent = frozenset(state.known_absent[player]) - {tile.a, tile.b}

    new_state = state.with_hand(player, hand).with_absent(player, absent)
    return replace(
        new_state,
        chain=chain,
        turn=1 - player,
        passes=0,
    )


def draw(state: GameState, rules: Rules) -> tuple[GameState, tuple[Tile, ...]]:
    """Добирает кости текущему игроку.

    Если ``rules.draw_until_playable``, тянем до первой играбельной кости.
    Если базар пуст и ходов нет — автоматически передаём ход.
    """
    player = state.turn
    left, right = state.left_end, state.right_end

    if state.can_move(player):
        return state, ()

    bazaar = list(state.bazaar)
    hand = list(state.hands[player])
    drawn: list[Tile] = []

    while bazaar:
        tile = bazaar.pop()
        hand.append(tile)
        drawn.append(tile)
        if has_move(hand, left, right):
            break
        if not rules.draw_until_playable:
            break

    stuck = not has_move(hand, left, right)
    # Достоверный вывод: раз ходов нет даже с новыми костями, значит концов
    # цепочки у игрока точно нет. Если ход появился — прежние знания устарели.
    absent = frozenset({left, right}) if stuck else frozenset()

    new_state = state.with_hand(player, hand).with_absent(player, absent)
    new_state = replace(
        new_state,
        bazaar=tuple(bazaar),
        drawn=(
            state.drawn[0] + len(drawn),
            state.drawn[1],
        )
        if player == 0
        else (
            state.drawn[0],
            state.drawn[1] + len(drawn),
        ),
    )

    if stuck:
        new_state = pass_turn(new_state)
        return new_state, tuple(drawn)

    return new_state, tuple(drawn)


def pass_turn(state: GameState) -> GameState:
    """Передаёт ход. Счётчик пасов нужен для определения блокировки."""
    return replace(state, turn=1 - state.turn, passes=state.passes + 1)


def blocked_outcome(state: GameState, rules: Rules) -> Outcome:
    mine, theirs = state.pips_of(0), state.pips_of(1)

    if not rules.pips_on_blocked:
        return Outcome(-1, 'blocked', 0)

    if mine < theirs:
        return Outcome(0, 'blocked', theirs)
    if theirs < mine:
        return Outcome(1, 'blocked', mine)
    return Outcome(-1, 'blocked', 0)


def check_game(state: GameState, rules: Rules) -> Outcome | None:
    """Возвращает результат партии или None, если игра продолжается."""
    if not state.hands[0]:
        return Outcome(0, 'empty_hand', state.pips_of(1))
    if not state.hands[1]:
        return Outcome(1, 'empty_hand', state.pips_of(0))
    if state.is_blocked:
        return blocked_outcome(state, rules)
    return None
