"""Средний уровень: вероятностная эвристика + точный эндшпиль.

Ключевая идея: ход хорош, если у соперника мало шансов ответить, а у нас
остаётся много возможностей. В отличие от ИИ первой версии здесь считается не
«сколько раз масть встретилась в видимых костях», а вероятность того, что у
соперника вообще есть подходящая кость — по гипергеометрическому
распределению невидимых костей. Дополнительно учитываются признаки исходной
эвристики: сколько костей этой масти уже в цепочке, сколько их у нас на руке,
насколько дубль закрывает конец.

В эндшпиле (базар пуст, суммарно ≤10 костей) подключается точный решатель,
поэтому уровень не отдаёт выигранные позиции.

Веса подобраны эволюционным поиском в ``tools/search.py`` на десятках тысяч
партий против ИИ первой версии.
"""

from __future__ import annotations

import random
from dataclasses import replace

from domino.ai.base import PolicyBase
from domino.ai.knowledge import Knowledge
from domino.ai.rollout import pimc_choose
from domino.ai.solver import EndgameSolver
from domino.engine import FULL_SET, GameState, Move, Rules, ends_after


class MediumPolicy(PolicyBase):
    name = 'medium'

    #: Штраф за вероятность ответа соперника.
    W_OPPONENT_OUTS = 3.4
    #: Штраф за ожидаемое число подходящих костей у соперника.
    W_EXPECTED = 1.75
    #: Бонус за кости масти, уже лежащие в цепочке.
    W_CHAIN = 1.0
    #: Бонус за свои кости этой масти.
    W_OWN = 0.5
    #: Бонус за дубль.
    W_DOUBLE = 2.1
    #: Бонус за сброс очков.
    W_PIPS = 0.15
    #: Бонус за сведение обоих концов к одной масти.
    W_SAME_ENDS = 0.9
    #: Бонус, когда соперник не может ответить вообще.
    W_DEAD_ALL = 1.15
    #: Бонус за свои кости к новым концам.
    W_FLEX = 0.6
    #: Штраф за «мёртвые» кости на руке в эндшпиле.
    W_TIGHT_ENDGAME = -0.3
    #: С какого размера руки включается эндшпильный штраф.
    ENDGAME_HAND = 3
    #: При скольких костях на руках (и пустом базаре) включается решатель.
    SOLVER_LIMIT = 10
    #: Короткий PIMC: число миров и глубина доигрывания.
    SAMPLES = 6
    HORIZON = 12
    #: Сколько лучших по эвристике ходов просчитывать.
    TOP_K = 2
    #: Вес априорной (эвристической) оценки в итоговом решении.
    STATIC_WEIGHT = 0.5

    def choose(
        self,
        state: GameState,
        me: int,
        rng: random.Random,
        rules: Rules | None = None,
    ) -> Move:
        if state.turn != me:
            state = replace(state, turn=me)
        moves = state.legal_moves(me)
        if not moves:  # pragma: no cover - вызывающий обязан проверить
            raise ValueError('Нет легальных ходов')
        if len(moves) == 1:
            return moves[0]

        rules = rules or Rules()
        move = self._solve_endgame(state, rules)
        if move is not None:
            return move

        knowledge = Knowledge.build(state, me)
        static = {move: self.score(state, me, knowledge, move) for move in moves}

        if not knowledge.candidates or not knowledge.opponent_count:
            best = max(static.values())
            return rng.choice([m for m, value in static.items() if value >= best - 1e-9])

        move, _, _ = pimc_choose(
            state,
            me,
            rng,
            rules,
            policy=self,
            static_scores=static,
            samples=self.SAMPLES,
            horizon=self.HORIZON,
            top_k=self.TOP_K,
            static_weight=self.STATIC_WEIGHT,
        )
        return move

    # -- оценка -------------------------------------------------------------

    def score(
        self,
        state: GameState,
        me: int,
        knowledge: Knowledge,
        move: Move,
    ) -> float:
        tile = move.tile
        left, right = ends_after(state.left_end, state.right_end, move)
        rest = [t for t in state.hands[me] if t != tile]

        left_chance = knowledge.reply_chance(left)
        right_chance = knowledge.reply_chance(right)
        left_expected = knowledge.expected_in_hand(left)
        right_expected = knowledge.expected_in_hand(right)

        chain = state.chain
        score = -self.W_OPPONENT_OUTS * (left_chance + right_chance)
        score -= self.W_EXPECTED * (left_expected + right_expected)

        score += self.W_CHAIN * (
            sum(1 for slot in chain if slot.tile.has(left))
            + sum(1 for slot in chain if slot.tile.has(right))
        )
        score += self.W_OWN * (
            sum(1 for t in rest if t.has(left)) + sum(1 for t in rest if t.has(right))
        )

        if tile.is_double:
            score += self.W_DOUBLE
        score += self.W_PIPS * tile.pips

        if left == right:
            score += self.W_SAME_ENDS
        if left_chance == 0 and right_chance == 0:
            score += self.W_DEAD_ALL

        score += self.W_FLEX * sum(1 for t in rest if t.has(left) or t.has(right))
        if len(rest) <= self.ENDGAME_HAND:
            score += self.W_TIGHT_ENDGAME * sum(
                1 for t in rest if not t.has(left) and not t.has(right)
            )
        return score

    # -- эндшпиль -----------------------------------------------------------

    def _solve_endgame(self, state: GameState, rules: Rules | None) -> Move | None:
        if state.bazaar:
            return None
        remaining = len(state.hands[0]) + len(state.hands[1])
        if remaining > self.SOLVER_LIMIT:
            return None
        # Бюджет страхует интерфейс от долгих позиций.
        move, _ = EndgameSolver(rules or Rules(), time_limit_s=0.25).best(state)
        return move

    @staticmethod
    def _unseen(state: GameState, me: int) -> list:
        visible = set(state.hands[me]) | {slot.tile for slot in state.chain}
        return [tile for tile in FULL_SET if tile not in visible]
