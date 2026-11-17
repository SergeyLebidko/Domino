"""Три визуальные темы игры.

Тема — это только данные: цвета, радиусы, шрифтовые предпочтения. Всё, что
зависит от темы, рендерится в кэш (см. ``domino.ui.assets``), поэтому
переключение темы не требует перезапуска.
"""

from __future__ import annotations

from dataclasses import dataclass

Color = tuple[int, int, int]
ColorA = tuple[int, int, int, int]


@dataclass(frozen=True)
class Theme:
    key: str
    title: str
    # Фон
    bg_top: Color
    bg_bottom: Color
    style: str  # 'flat' | 'felt' | 'wood' | 'paper'
    pattern_alpha: int
    #: Сила затемнения по краю окна: на светлых темах нужна слабее.
    vignette_alpha: int
    # Поверхности
    board: Color
    board_edge: Color
    panel: Color
    panel_alt: Color
    panel_edge: Color
    # Текст
    text: Color
    text_dim: Color
    text_inverse: Color
    # Акценты
    accent: Color
    accent_hover: Color
    accent_text: Color
    # Стороны
    player: Color
    ai: Color
    success: Color
    danger: Color
    shadow: ColorA
    # Геометрия и шрифты
    radius: int
    #: Радиус скругления кости — задаёт подсветку конца при перетаскивании.
    tile_radius: int
    heading_font: str  # 'sans' | 'serif'
    body_font: str


FLAT_DARK = Theme(
    key='flat_dark',
    title='Графит',
    bg_top=(21, 25, 32),
    bg_bottom=(12, 15, 20),
    style='flat',
    pattern_alpha=10,
    vignette_alpha=70,
    board=(30, 36, 45),
    board_edge=(45, 53, 64),
    panel=(33, 39, 49),
    panel_alt=(41, 48, 60),
    panel_edge=(56, 65, 79),
    text=(234, 238, 244),
    text_dim=(148, 160, 178),
    text_inverse=(18, 22, 28),
    accent=(47, 198, 176),
    accent_hover=(72, 219, 197),
    accent_text=(6, 32, 29),
    player=(47, 198, 176),
    ai=(232, 118, 108),
    success=(94, 204, 132),
    danger=(232, 118, 108),
    shadow=(0, 0, 0, 110),
    radius=14,
    tile_radius=9,
    heading_font='sans',
    body_font='sans',
)

CLUB_GREEN = Theme(
    key='club_green',
    title='Клуб',
    bg_top=(28, 92, 58),
    bg_bottom=(14, 58, 37),
    style='felt',
    pattern_alpha=16,
    vignette_alpha=70,
    board=(24, 82, 52),
    board_edge=(122, 88, 48),
    panel=(30, 52, 40),
    panel_alt=(38, 64, 49),
    panel_edge=(122, 96, 58),
    text=(243, 236, 218),
    text_dim=(186, 194, 176),
    text_inverse=(26, 34, 26),
    accent=(217, 180, 90),
    accent_hover=(236, 202, 118),
    accent_text=(38, 30, 12),
    player=(126, 214, 152),
    ai=(230, 140, 120),
    success=(126, 214, 152),
    danger=(230, 140, 120),
    shadow=(0, 0, 0, 120),
    radius=10,
    tile_radius=6,
    heading_font='serif',
    body_font='sans',
)

WARM_WOOD = Theme(
    key='warm_wood',
    title='Дерево',
    bg_top=(88, 58, 40),
    bg_bottom=(56, 36, 26),
    style='wood',
    pattern_alpha=18,
    vignette_alpha=70,
    board=(74, 49, 34),
    board_edge=(46, 30, 21),
    panel=(95, 66, 46),
    panel_alt=(110, 78, 55),
    panel_edge=(140, 104, 74),
    text=(248, 238, 224),
    text_dim=(206, 186, 166),
    text_inverse=(46, 30, 21),
    accent=(224, 148, 86),
    accent_hover=(242, 172, 112),
    accent_text=(48, 26, 12),
    player=(246, 186, 120),
    ai=(214, 112, 96),
    success=(168, 208, 130),
    danger=(214, 112, 96),
    shadow=(0, 0, 0, 120),
    radius=12,
    tile_radius=7,
    heading_font='serif',
    body_font='sans',
)

LINEN = Theme(
    key='linen',
    title='Лён',
    bg_top=(224, 214, 196),
    bg_bottom=(203, 191, 171),
    style='paper',
    pattern_alpha=12,
    #: Светлый фон не нужно сильно затемнять — иначе кайма станет грязной.
    vignette_alpha=34,
    #: Поле чуть светлее фона, панели — почти белые: на светлом столе
    #: панели иначе сливаются с фоном.
    board=(238, 230, 216),
    board_edge=(178, 163, 140),
    panel=(250, 246, 238),
    panel_alt=(255, 252, 246),
    panel_edge=(196, 183, 162),
    text=(58, 50, 40),
    text_dim=(124, 112, 96),
    text_inverse=(250, 246, 238),
    accent=(178, 112, 58),
    accent_hover=(200, 132, 74),
    accent_text=(255, 249, 240),
    player=(60, 132, 92),
    ai=(190, 86, 66),
    success=(60, 140, 96),
    danger=(190, 86, 66),
    shadow=(48, 38, 26, 90),
    radius=12,
    tile_radius=8,
    heading_font='serif',
    body_font='sans',
)

SKY = Theme(
    key='sky',
    title='Небо',
    bg_top=(203, 219, 238),
    bg_bottom=(181, 200, 223),
    style='paper',
    pattern_alpha=12,
    vignette_alpha=34,
    board=(226, 236, 248),
    board_edge=(150, 173, 200),
    panel=(244, 250, 255),
    panel_alt=(252, 254, 255),
    panel_edge=(166, 190, 216),
    text=(38, 52, 70),
    text_dim=(104, 124, 148),
    text_inverse=(240, 247, 253),
    accent=(52, 108, 178),
    accent_hover=(72, 128, 200),
    accent_text=(244, 250, 255),
    player=(44, 124, 92),
    ai=(186, 82, 96),
    success=(44, 132, 96),
    danger=(186, 82, 96),
    shadow=(38, 52, 74, 90),
    radius=12,
    tile_radius=8,
    heading_font='sans',
    body_font='sans',
)

THEMES: dict[str, Theme] = {
    FLAT_DARK.key: FLAT_DARK,
    CLUB_GREEN.key: CLUB_GREEN,
    WARM_WOOD.key: WARM_WOOD,
    LINEN.key: LINEN,
    SKY.key: SKY,
}

THEME_ORDER = (
    FLAT_DARK.key,
    CLUB_GREEN.key,
    WARM_WOOD.key,
    LINEN.key,
    SKY.key,
)


def get_theme(key: str) -> Theme:
    return THEMES.get(key, FLAT_DARK)


def next_theme(key: str) -> Theme:
    try:
        index = THEME_ORDER.index(key)
    except ValueError:
        index = -1
    return THEMES[THEME_ORDER[(index + 1) % len(THEME_ORDER)]]
