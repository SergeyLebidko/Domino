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
    style: str  # 'flat' | 'felt' | 'wood'
    pattern_alpha: int
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
    # Кости
    tile_face: Color
    tile_face_edge: Color
    tile_edge: Color
    pip: Color
    tile_back: Color
    tile_back_pattern: Color
    # Стороны
    player: Color
    ai: Color
    success: Color
    danger: Color
    shadow: ColorA
    # Геометрия и шрифты
    radius: int
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
    tile_face=(244, 241, 233),
    tile_face_edge=(214, 208, 194),
    tile_edge=(168, 160, 144),
    pip=(37, 43, 52),
    tile_back=(58, 67, 82),
    tile_back_pattern=(72, 83, 101),
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
    tile_face=(248, 243, 228),
    tile_face_edge=(226, 216, 192),
    tile_edge=(184, 168, 132),
    pip=(45, 40, 32),
    tile_back=(96, 70, 40),
    tile_back_pattern=(120, 90, 54),
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
    tile_face=(250, 242, 224),
    tile_face_edge=(232, 220, 196),
    tile_edge=(196, 176, 148),
    pip=(70, 48, 34),
    tile_back=(122, 84, 58),
    tile_back_pattern=(146, 104, 72),
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

THEMES: dict[str, Theme] = {
    FLAT_DARK.key: FLAT_DARK,
    CLUB_GREEN.key: CLUB_GREEN,
    WARM_WOOD.key: WARM_WOOD,
}

THEME_ORDER = (FLAT_DARK.key, CLUB_GREEN.key, WARM_WOOD.key)


def get_theme(key: str) -> Theme:
    return THEMES.get(key, FLAT_DARK)


def next_theme(key: str) -> Theme:
    try:
        index = THEME_ORDER.index(key)
    except ValueError:
        index = -1
    return THEMES[THEME_ORDER[(index + 1) % len(THEME_ORDER)]]
