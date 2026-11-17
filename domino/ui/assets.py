"""Кэш ресурсов: фоны, шрифты, грани костей, тени.

Всё, что дорого рисовать, создаётся один раз на тему и переиспользуется.
При смене темы кэш очищается.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pygame as pg

from domino.ui.theme import Theme
from domino.ui.tiles import TileSkin, get_skin

#: Раскладка точек на половинке кости в координатах [-1, 0, 1].
PIP_LAYOUT: dict[int, tuple[tuple[int, int], ...]] = {
    0: (),
    1: ((0, 0),),
    2: ((-1, -1), (1, 1)),
    3: ((-1, -1), (0, 0), (1, 1)),
    4: ((-1, -1), (-1, 1), (1, -1), (1, 1)),
    5: ((-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)),
    6: ((-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)),
}

#: Насколько широко разносить точки по половинке кости.
PIP_SPREAD = 0.70

FONT_CANDIDATES = {
    'sans': ('dejavusans', 'liberationsans', 'notosans', 'freesans', 'arial'),
    'serif': ('dejavuserif', 'liberationserif', 'notoserif', 'freeserif', 'georgia'),
}

#: Шрифты лежат в папке игры: одинаковый вид на Windows, Linux и macOS.
FONT_DIR = Path(__file__).resolve().parent.parent.parent / 'assets' / 'fonts'

BUNDLED_FONTS = {
    ('sans', False): 'DejaVuSans.ttf',
    ('sans', True): 'DejaVuSans-Bold.ttf',
    ('serif', False): 'DejaVuSerif.ttf',
    ('serif', True): 'DejaVuSerif-Bold.ttf',
}


@dataclass(frozen=True)
class TileSprite:
    """Готовая картинка кости с полями под тень."""

    surface: pg.Surface
    pad: int
    width: int
    height: int

    def blit_at(self, target: pg.Surface, x: int, y: int) -> pg.Rect:
        target.blit(self.surface, (x - self.pad, y - self.pad))
        return pg.Rect(x, y, self.width, self.height)


class Assets:
    def __init__(self, theme: Theme, size: tuple[int, int],
                 skin: TileSkin | str | None = None) -> None:
        self.theme = theme
        self.skin = get_skin(skin) if isinstance(skin, str) or skin is None else skin
        self.size = size
        self._fonts: dict[tuple[int, bool, str], pg.font.Font] = {}
        self._tiles: dict[tuple[int, int, bool, int], TileSprite] = {}
        self._backs: dict[tuple[int, bool], TileSprite] = {}
        self._glow: dict[tuple[int, int, bool], pg.Surface] = {}
        self._shadows: dict[tuple[int, int, int], pg.Surface] = {}
        self._background: pg.Surface | None = None
        self._board: pg.Surface | None = None

    # -- тема ---------------------------------------------------------------

    def set_theme(self, theme: Theme) -> None:
        if theme == self.theme:
            return
        self.theme = theme
        self._tiles.clear()
        self._backs.clear()
        self._glow.clear()
        self._shadows.clear()
        self._background = None
        self._board = None

    def set_skin(self, skin: TileSkin | str) -> None:
        """Меняет набор костей. Тема стола остаётся прежней."""
        resolved = get_skin(skin) if isinstance(skin, str) else skin
        if resolved == self.skin:
            return
        self.skin = resolved
        self._tiles.clear()
        self._backs.clear()

    # -- шрифты -------------------------------------------------------------

    def font(self, size: int, bold: bool = False, kind: str = 'sans') -> pg.font.Font:
        key = (size, bold, kind)
        font = self._fonts.get(key)
        if font is None:
            font = self._load_font(size, bold, kind)
            self._fonts[key] = font
        return font

    @staticmethod
    def _load_font(size: int, bold: bool, kind: str) -> pg.font.Font:
        """Сначала шрифт из папки игры, затем системный, затем встроенный."""
        bundled = BUNDLED_FONTS.get((kind, bold)) or BUNDLED_FONTS[('sans', bold)]
        path = FONT_DIR / bundled
        if path.exists():
            return pg.font.Font(str(path), size)

        for name in FONT_CANDIDATES.get(kind, FONT_CANDIDATES['sans']):
            found = pg.font.match_font(name, bold=bold)
            if found:
                return pg.font.Font(found, size)

        # Крайний случай: встроенный шрифт pygame не содержит кириллицы,
        # поэтому размер увеличиваем — латиница останется читаемой.
        font = pg.font.Font(None, size)
        if bold:
            font.set_bold(True)
        return font

    def heading(self, size: int) -> pg.font.Font:
        return self.font(size, bold=True, kind=self.theme.heading_font)

    def body(self, size: int, bold: bool = False) -> pg.font.Font:
        return self.font(size, bold=bold, kind=self.theme.body_font)

    # -- фон ----------------------------------------------------------------

    @property
    def background(self) -> pg.Surface:
        if self._background is None:
            self._background = render_background(self.theme, self.size)
        return self._background

    # -- кости --------------------------------------------------------------

    def tile(self, first: int, second: int, vertical: bool, cell: int) -> TileSprite:
        key = (first, second, vertical, cell)
        sprite = self._tiles.get(key)
        if sprite is None:
            sprite = render_tile(self.skin, first, second, vertical, cell)
            self._tiles[key] = sprite
        return sprite

    def tile_back(self, cell: int, vertical: bool = True) -> TileSprite:
        key = (cell, vertical)
        sprite = self._backs.get(key)
        if sprite is None:
            sprite = render_tile_back(self.skin, cell, vertical)
            self._backs[key] = sprite
        return sprite

    def glow(self, width: int, height: int, vertical: bool = False) -> pg.Surface:
        key = (width, height, vertical)
        surface = self._glow.get(key)
        if surface is None:
            surface = render_glow(self.theme, width, height)
            self._glow[key] = surface
        return surface

    def shadow(self, width: int, height: int, radius: int) -> pg.Surface:
        key = (width, height, radius)
        surface = self._shadows.get(key)
        if surface is None:
            surface = render_shadow(self.theme, width, height, radius)
            self._shadows[key] = surface
        return surface


# -- рисование -------------------------------------------------------------


def render_background(theme: Theme, size: tuple[int, int]) -> pg.Surface:
    width, height = size
    surface = pg.Surface(size).convert()
    top, bottom = theme.bg_top, theme.bg_bottom

    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pg.draw.line(surface, color, (0, y), (width, y))

    if theme.style == 'flat':
        _draw_flat_pattern(surface, theme)
    elif theme.style == 'felt':
        _draw_felt_pattern(surface, theme)
    else:
        _draw_wood_pattern(surface, theme)

    _draw_vignette(surface)
    return surface


def _draw_flat_pattern(surface: pg.Surface, theme: Theme) -> None:
    layer = pg.Surface(surface.get_size(), pg.SRCALPHA)
    step = 36
    color = (*theme.accent, theme.pattern_alpha)
    for x in range(0, surface.get_width(), step):
        for y in range(0, surface.get_height(), step):
            pg.draw.circle(layer, color, (x, y), 1)

    # Мягкое свечение акцента в верхней части поля.
    glow = pg.Surface((surface.get_width(), 420), pg.SRCALPHA)
    for i in range(40, 0, -1):
        alpha = int(theme.pattern_alpha * 1.6 * (i / 40) ** 2)
        radius = int(surface.get_width() * 0.55 * i / 40)
        pg.draw.ellipse(
            glow,
            (*theme.accent, alpha),
            (
                surface.get_width() // 2 - radius,
                210 - radius // 3,
                radius * 2,
                radius // 2,
            ),
        )
    layer.blit(glow, (0, 0), special_flags=pg.BLEND_ADD)
    surface.blit(layer, (0, 0))


def _draw_felt_pattern(surface: pg.Surface, theme: Theme) -> None:
    rng = random.Random(17)
    layer = pg.Surface(surface.get_size(), pg.SRCALPHA)
    for _ in range(5200):
        x = rng.randrange(surface.get_width())
        y = rng.randrange(surface.get_height())
        shade = rng.choice((18, 26, 40))
        pg.draw.circle(layer, (255, 255, 255, shade), (x, y), 1)

    # Деревянная рамка по краю — визуальная «рамка стола».
    frame = 22
    wood = (86, 58, 32)
    wood_dark = (64, 42, 22)
    for offset, color in ((0, wood_dark), (4, wood), (frame - 6, wood)):
        pg.draw.rect(layer, color, (offset, offset, surface.get_width() - offset * 2, surface.get_height() - offset * 2), frame)
    inner = frame
    pg.draw.rect(
        layer,
        (*theme.board_edge, 190),
        (inner, inner, surface.get_width() - inner * 2, surface.get_height() - inner * 2),
        3,
    )
    surface.blit(layer, (0, 0))


def _draw_wood_pattern(surface: pg.Surface, theme: Theme) -> None:
    rng = random.Random(5)
    layer = pg.Surface(surface.get_size(), pg.SRCALPHA)
    width, height = surface.get_size()

    # Доски: вертикальные полосы разной светлоты.
    plank = 96
    for index, x in enumerate(range(0, width, plank)):
        shade = 10 if index % 2 else -6
        color = tuple(max(0, min(255, c + shade)) for c in theme.bg_bottom)
        pg.draw.rect(layer, (*color, 120), (x, 0, plank, height))
        pg.draw.line(layer, (0, 0, 0, 60), (x, 0), (x, height), 2)

    # Волокна древесины.
    for _ in range(260):
        x = rng.randrange(width)
        y = rng.randrange(height)
        length = rng.randint(40, 200)
        alpha = rng.randint(8, 22)
        pg.draw.line(layer, (30, 18, 10, alpha), (x, y), (x + rng.randint(-6, 6), y + length), 1)

    surface.blit(layer, (0, 0))


def _draw_vignette(surface: pg.Surface) -> None:
    width, height = surface.get_size()
    layer = pg.Surface(surface.get_size(), pg.SRCALPHA)
    band = 140
    for i in range(band):
        alpha = int(70 * (1 - i / band) ** 2)
        color = (0, 0, 0, alpha)
        pg.draw.rect(layer, color, (i, i, width - i * 2, height - i * 2), 1)
    surface.blit(layer, (0, 0))


def render_tile(
    skin: TileSkin,
    first: int,
    second: int,
    vertical: bool,
    cell: int,
) -> TileSprite:
    pad = max(5, cell // 7)
    if vertical:
        width, height = cell, 2 * cell
    else:
        width, height = 2 * cell, cell

    surface = pg.Surface((width + 2 * pad, height + 2 * pad), pg.SRCALPHA)
    radius = max(3, int(skin.radius * cell / 56))

    # Тень.
    shadow = pg.Surface((width, height), pg.SRCALPHA)
    pg.draw.rect(shadow, (0, 0, 0, 110), shadow.get_rect(), border_radius=radius)
    blur = max(2, cell // 12)
    shadow = pg.transform.gaussian_blur(shadow, blur)
    surface.blit(shadow, (pad + 1, pad + max(2, cell // 14)))

    face = pg.Rect(pad, pad, width, height)
    pg.draw.rect(surface, skin.face_edge, face, border_radius=radius)
    inner = face.inflate(-2, -2)
    pg.draw.rect(surface, skin.face, inner, border_radius=max(2, radius - 1))

    # Блик сверху: плавный градиент, иначе на тёмных костях он читается
    # как резкая светлая полоса.
    if skin.gloss > 0:
        highlight = pg.Surface((inner.width, inner.height), pg.SRCALPHA)
        band = max(2, int(inner.height * 0.42))
        for index in range(band):
            alpha = int(skin.gloss * (1 - index / band) ** 1.4)
            if alpha <= 0:
                continue
            pg.draw.line(highlight, (255, 255, 255, alpha),
                         (0, index), (inner.width, index))
        mask = pg.Surface((inner.width, inner.height), pg.SRCALPHA)
        pg.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                     border_radius=max(2, radius - 1))
        highlight.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        surface.blit(highlight, inner.topleft)

    # Разделитель между половинками.
    if vertical:
        y = pad + cell
        pg.draw.line(surface, skin.divider, (pad + cell // 7, y),
                     (pad + width - cell // 7, y), max(1, cell // 40))
        halves = (
            pg.Rect(pad, pad, width, cell),
            pg.Rect(pad, pad + cell, width, cell),
        )
    else:
        x = pad + cell
        pg.draw.line(surface, skin.divider, (x, pad + cell // 7),
                     (x, pad + height - cell // 7), max(1, cell // 40))
        halves = (
            pg.Rect(pad, pad, cell, height),
            pg.Rect(pad + cell, pad, cell, height),
        )

    pip_radius = max(2, int(cell * 0.082))
    inset = cell * 0.24
    for rect, value in zip(halves, (first, second)):
        _draw_pips(surface, skin, rect, value, pip_radius, inset)

    return TileSprite(surface, pad, width, height)


def _draw_pips(
    surface: pg.Surface,
    skin: TileSkin,
    half: pg.Rect,
    value: int,
    radius: int,
    inset: float,
) -> None:
    """Точки на половинке кости.

    Шаг между точками ограничен снизу их диаметром с зазором: на мелких
    костях (логотип, превью) точки иначе слипаются в одно пятно.
    """
    cx, cy = half.center
    usable = min(half.width, half.height) / 2 - inset
    layout = PIP_LAYOUT[value]

    # Максимальное смещение по сетке [-1..1] определяет шаг.
    spread = usable * skin.pip_spread
    # Минимальный шаг, при котором точки не касаются: диаметр + зазор.
    minimum = radius * 2 + max(1, radius // 2)
    step_x = step_y = max(spread, minimum)
    # Но за пределы половинки кости выходить нельзя.
    limit = min(half.width, half.height) / 2 - radius - 1
    step_x = min(step_x, limit)
    step_y = min(step_y, limit)

    inset_style = skin.pip_style == 'inset' and radius >= 3
    for gx, gy in layout:
        x = int(cx + gx * step_x)
        y = int(cy + gy * step_y)
        if inset_style:
            # Вдавленная точка: сверху тень, снизу светлый край — как резьба.
            _draw_inset_pip(surface, skin, x, y, radius)
        elif radius >= 3:
            pg.draw.aacircle(surface, skin.pip, (x, y), radius)
            pg.draw.aacircle(surface, skin.pip, (x, y), radius - 1)
        else:
            pg.draw.circle(surface, skin.pip, (x, y), radius)


def _draw_inset_pip(surface: pg.Surface, skin: TileSkin, x: int, y: int, radius: int) -> None:
    """Углублённая точка: тень сверху-слева, подсветка снизу-справа."""
    dark = tuple(max(0, c - 42) for c in skin.face)
    light = tuple(min(255, c + 54) for c in skin.face)
    pg.draw.circle(surface, light, (x + 1, y + 1), radius)
    pg.draw.circle(surface, dark, (x - 1, y - 1), radius - 1)
    pg.draw.aacircle(surface, skin.pip, (x, y), max(1, radius - 2))


def render_tile_back(skin: TileSkin, cell: int, vertical: bool = True) -> TileSprite:
    pad = max(4, cell // 7)
    if vertical:
        width, height = cell, 2 * cell
    else:
        width, height = 2 * cell, cell
    surface = pg.Surface((width + 2 * pad, height + 2 * pad), pg.SRCALPHA)
    radius = max(3, int(skin.radius * cell / 56))

    shadow = pg.Surface((width, height), pg.SRCALPHA)
    pg.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=radius)
    shadow = pg.transform.gaussian_blur(shadow, max(2, cell // 12))
    surface.blit(shadow, (pad + 1, pad + 2))

    face = pg.Rect(pad, pad, width, height)
    pg.draw.rect(surface, skin.back, face, border_radius=radius)

    cx, cy = face.center
    if skin.back_style == 'frame':
        _draw_back_frame(surface, skin, face, radius)
    elif skin.back_style == 'lattice':
        _draw_back_lattice(surface, skin, face)
    else:
        _draw_back_diamond(surface, skin, face, cell, cx, cy)

    return TileSprite(surface, pad, width, height)


def _draw_back_diamond(
    surface: pg.Surface,
    skin: TileSkin,
    face: pg.Rect,
    cell: int,
    cx: int,
    cy: int,
) -> None:
    """Ромб по центру — «рубашка».

    Рисуем линиями: у draw.polygon с толщиной чернила ложатся несимметрично
    (сдвиг +1 px). Полуразмер берём чётным, чтобы полная высота ромба делилась
    на два без остатка — иначе при чётной высоте кости он смещается.
    """
    pg.draw.rect(surface, skin.back_pattern, face.inflate(-2, -2), 2,
                 border_radius=max(2, max(3, int(skin.radius * cell / 56)) - 1))
    step = cell // 5
    if step % 2:
        step += 1
    corners = [
        (cx, cy - step),
        (cx + step, cy),
        (cx, cy + step),
        (cx - step, cy),
    ]
    for index in range(4):
        pg.draw.line(surface, skin.back_pattern,
                     corners[index], corners[(index + 1) % 4], 1)
    pg.draw.line(surface, skin.back_pattern,
                 (face.left + 4, cy), (face.right - 4, cy), 1)


def _draw_back_frame(surface: pg.Surface, skin: TileSkin, face: pg.Rect, radius: int) -> None:
    """Рамка с заполненным ядром — строгий «оникс»."""
    margin = max(4, face.width // 10)
    outer = face.inflate(-2 * margin, -2 * margin)
    pg.draw.rect(surface, skin.back_pattern, outer, 2, border_radius=max(2, radius - 2))

    inner = outer.inflate(-max(4, face.width // 7), -max(4, face.width // 7))
    if inner.width > 6 and inner.height > 6:
        # Ядро чуть светлее рамки: на мелких костях иначе видна только рамка.
        core = tuple(min(255, c + 14) for c in skin.back)
        pg.draw.rect(surface, core, inner, border_radius=max(1, radius - 4))
        pg.draw.rect(surface, skin.back_pattern, inner, 1, border_radius=max(1, radius - 4))
        pg.draw.circle(surface, skin.back_pattern, inner.center, max(2, face.width // 16))


def _draw_back_lattice(surface: pg.Surface, skin: TileSkin, face: pg.Rect) -> None:
    """Диагональная сетка — тёплая «янтарная» рубашка."""
    pg.draw.rect(surface, skin.back_pattern, face.inflate(-2, -2), 2,
                 border_radius=max(2, int(skin.radius * face.width / 56) - 1))

    layer = pg.Surface(face.size, pg.SRCALPHA)
    step = max(6, face.width // 4)
    width, height = layer.get_size()
    for offset in range(-height, width, step):
        pg.draw.line(layer, (*skin.back_pattern, 150), (offset, 0), (offset + height, height), 1)
        pg.draw.line(layer, (*skin.back_pattern, 150), (offset + height, 0), (offset, height), 1)

    # Сетка не должна вылезать за скруглённые углы.
    mask = pg.Surface(face.size, pg.SRCALPHA)
    pg.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                 border_radius=max(2, int(skin.radius * face.width / 56)))
    layer.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
    surface.blit(layer, face.topleft)


def render_glow(theme: Theme, width: int, height: int, vertical: bool = False) -> pg.Surface:
    margin = 18
    surface = pg.Surface((width + margin * 2, height + margin * 2), pg.SRCALPHA)
    radius = max(6, theme.tile_radius * 2)
    for spread in range(margin, 0, -1):
        alpha = int(int(120 * (1 - spread / margin) ** 1.4))
        if alpha <= 0:
            continue
        rect = pg.Rect(margin - spread, margin - spread, width + spread * 2, height + spread * 2)
        pg.draw.rect(surface, (*theme.accent, alpha), rect, 3, border_radius=radius + spread)
    return surface


def render_shadow(theme: Theme, width: int, height: int, radius: int) -> pg.Surface:
    margin = 20
    surface = pg.Surface((width + margin * 2, height + margin * 2), pg.SRCALPHA)
    rect = pg.Rect(margin, margin, width, height)
    pg.draw.rect(surface, theme.shadow, rect, border_radius=radius)
    return pg.transform.gaussian_blur(surface, 8)


@lru_cache(maxsize=4096)
def text_image(font: pg.font.Font, value: str, color: tuple[int, int, int]) -> pg.Surface:
    """Кэш отрендеренного текста: рисование одной и той же строки дёшево."""
    return font.render(value, True, color)


def clear_text_cache() -> None:
    text_image.cache_clear()
