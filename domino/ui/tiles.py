"""Наборы оформления костей — независимо от темы стола.

Тема стола отвечает за фон, панели и акценты; набор костей — за сами костяшки.
Они комбинируются свободно: любая тема с любым набором.

Набор — это только данные (цвета, стиль точек, стиль рубашки, геометрия).
Рендер живёт в :mod:`domino.ui.assets` и кэшируется по набору.
"""

from __future__ import annotations

from dataclasses import dataclass

from domino.settings import CELL

Color = tuple[int, int, int]

#: Стили точек: круглые «наклеенные» или вдавленные с тенью.
PIP_STYLES = ('round', 'inset')

#: Стили рубашки: ромб, двойная рамка, диагональная сетка.
BACK_STYLES = ('diamond', 'frame', 'lattice')


@dataclass(frozen=True)
class TileSkin:
    """Оформление костяшек, независимое от темы стола."""

    key: str
    title: str
    # Лицо
    face: Color
    face_edge: Color
    divider: Color
    # Точки
    pip: Color
    pip_style: str
    #: Сила верхнего блика, 0…80 (альфа белого).
    gloss: int
    # Рубашка
    back: Color
    back_pattern: Color
    back_style: str
    # Геометрия
    radius: int
    #: Насколько широко разносить точки, 0.5…0.9.
    pip_spread: float


BONE = TileSkin(
    key='bone',
    title='Кость',
    face=(246, 242, 231),
    face_edge=(216, 209, 193),
    divider=(176, 166, 147),
    pip=(35, 41, 50),
    pip_style='round',
    gloss=46,
    back=(58, 67, 82),
    back_pattern=(76, 88, 107),
    back_style='diamond',
    radius=9,
    pip_spread=0.70,
)

GRAPHITE = TileSkin(
    key='graphite',
    title='Оникс',
    face=(46, 53, 64),
    face_edge=(30, 36, 45),
    divider=(88, 99, 115),
    pip=(226, 236, 245),
    pip_style='round',
    gloss=70,
    back=(26, 32, 41),
    back_pattern=(104, 118, 138),
    back_style='frame',
    radius=8,
    pip_spread=0.72,
)

AMBER = TileSkin(
    key='amber',
    title='Янтарь',
    face=(236, 189, 126),
    face_edge=(198, 148, 90),
    divider=(150, 104, 58),
    pip=(92, 52, 26),
    pip_style='inset',
    gloss=34,
    back=(112, 74, 46),
    back_pattern=(158, 112, 70),
    back_style='lattice',
    radius=7,
    pip_spread=0.68,
)

SKINS: dict[str, TileSkin] = {
    BONE.key: BONE,
    GRAPHITE.key: GRAPHITE,
    AMBER.key: AMBER,
}

SKIN_ORDER = (BONE.key, GRAPHITE.key, AMBER.key)


def get_skin(key: str) -> TileSkin:
    return SKINS.get(key, BONE)


def next_skin(key: str) -> TileSkin:
    try:
        index = SKIN_ORDER.index(key)
    except ValueError:
        index = -1
    return SKINS[SKIN_ORDER[(index + 1) % len(SKIN_ORDER)]]


#: Размер половинки кости, по которому задан ``radius`` набора.
BASE_CELL = CELL
