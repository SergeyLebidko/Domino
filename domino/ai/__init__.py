"""Искусственный интеллект: уровни сложности и утилиты для замеров."""

from domino.ai.easy import EasyPolicy
from domino.ai.hard import HardPolicy
from domino.ai.medium import MediumPolicy
POLICIES = {
    'easy': EasyPolicy,
    'medium': MediumPolicy,
    'hard': HardPolicy,
}

DIFFICULTIES = ('easy', 'medium', 'hard')

DIFFICULTY_NAMES = {
    'easy': 'Новичок',
    'medium': 'Любитель',
    'hard': 'Мастер',
}

DIFFICULTY_DESCRIPTIONS = {
    'easy': 'Играет как человек, который только учится: ошибается и не считает.',
    'medium': 'Считает вероятности и старается закрыть вам концы.',
    'hard': 'Перебирает варианты и просчитывает партию наперёд.',
}


def make_policy(difficulty: str, **kwargs):
    """Создаёт стратегию по имени уровня сложности.

    Лишние параметры (например, ``samples`` для простых уровней) игнорируются.
    """
    try:
        factory = POLICIES[difficulty]
    except KeyError:
        raise ValueError(f'Неизвестный уровень сложности: {difficulty!r}') from None
    return factory(**_accepted_kwargs(factory, kwargs))


from domino.settings import (
    AI_HARD_BUDGET_MS,
    AI_HARD_ENDGAME,
    AI_HARD_HORIZON,
    AI_HARD_MIN_SAMPLES,
    AI_HARD_SAMPLES,
    AI_HARD_TOP_K,
)


def make_policy_for_ui(difficulty: str):
    """Стратегия с ограничением по времени — чтобы интерфейс не «залипал»."""
    if difficulty == 'hard':
        return HardPolicy(
            samples=AI_HARD_SAMPLES,
            horizon=AI_HARD_HORIZON,
            top_k=AI_HARD_TOP_K,
            min_samples=AI_HARD_MIN_SAMPLES,
            endgame_limit=AI_HARD_ENDGAME,
            time_guard_ms=AI_HARD_BUDGET_MS,
        )
    return make_policy(difficulty)


def _accepted_kwargs(factory, kwargs):
    import inspect

    parameters = inspect.signature(factory.__init__).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in parameters}
