"""Тесты фона: между панелями не должно быть декоративных обрывков.

Проверки не зависят от конкретных цветов: тема «Дерево» сама коричневая,
поэтому «похоже на дерево» — плохой критерий. Вместо этого считаем, каким
фон обязан быть по формуле градиента и винетки, и сверяем с картинкой.
"""

from __future__ import annotations

import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame as pg  # noqa: E402
import pytest  # noqa: E402

from domino import settings  # noqa: E402
from domino.ui.app import App  # noqa: E402
from domino.ui.assets import render_background  # noqa: E402
from domino.ui.scenes import GameScene, MenuScene  # noqa: E402
from domino.ui.theme import THEME_ORDER, get_theme  # noqa: E402

#: Ширина затемнения по краю из _draw_vignette.
VIGNETTE_BAND = 140


@pytest.fixture(scope='module')
def app():
    pg.init()
    application = App(headless=True)
    yield application
    pg.quit()


def _expected(theme, x: int, y: int) -> tuple[float, float, float]:
    """Цвет фона без узора: вертикальный градиент минус винетка."""
    height = settings.H
    t = y / max(1, height - 1)
    base = [theme.bg_top[i] + (theme.bg_bottom[i] - theme.bg_top[i]) * t
            for i in range(3)]

    depth = min(x, y, settings.W - 1 - x, settings.H - 1 - y)
    depth = min(depth, VIGNETTE_BAND - 1)
    alpha = int(theme.vignette_alpha * (1 - depth / VIGNETTE_BAND) ** 2)
    return tuple(channel * (1 - alpha / 255) for channel in base)


def _median_deviation(theme, points, background: pg.Surface | None = None) -> float:
    """Типичное отклонение каймы от ожидаемого градиента.

    Медиана, а не среднее: одиночные крапинки сукна не должны влиять.
    """
    if background is None:
        background = render_background(theme, (settings.W, settings.H))
    deviations = []
    for x, y in points:
        actual = background.get_at((x, y))[:3]
        expected = _expected(theme, x, y)
        deviations.append(
            sum(abs(actual[i] - expected[i]) for i in range(3)) / 3
        )
    deviations.sort()
    return deviations[len(deviations) // 2]


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_background_edge_matches_the_gradient(app, theme):
    """Регрессия: в теме «Клуб» по краю шла деревянная рамка 22 px.

    Она не влезала в зазор BOARD_MARGIN (18 px), поэтому между панелями
    торчали рваные полосы дерева, а сверху рамки не было — топбар её
    перекрывал. Теперь кайма совпадает с обычным градиентом фона.
    """
    palette = get_theme(theme)
    # Кайма по всем четырём сторонам, вглубь до бывшей рамки.
    points = []
    for depth in (1, 5, 9, 13, 17, 21):
        for step in range(40, settings.W - 40, 40):
            points.append((step, depth))
            points.append((step, settings.H - 1 - depth))
        for step in range(40, settings.H - 40, 40):
            points.append((depth, step))
            points.append((settings.W - 1 - depth, step))

    deviation = _median_deviation(palette, points)
    assert deviation < 12, (
        f'{theme}: кайма отличается от градиента на {deviation:.0f} — это рамка'
    )


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_background_corner_has_no_extra_layer(app, theme):
    """В углу нет второго слоя: там раньше сходились все полосы рамки."""
    palette = get_theme(theme)
    corners = []
    for depth in (0, 3, 6, 9, 12, 15, 18, 21):
        corners.append((depth, depth))
        corners.append((settings.W - 1 - depth, depth))
        corners.append((depth, settings.H - 1 - depth))
        corners.append((settings.W - 1 - depth, settings.H - 1 - depth))

    deviation = _median_deviation(palette, corners)
    assert deviation < 14, f'{theme}: в углах лишний слой ({deviation:.0f})'


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_gutters_between_panels_show_plain_background(app, theme):
    """Регрессия: в зазорах между панелями проглядывали обрывки дерева."""
    fresh = App(theme=theme, headless=True)
    scene = GameScene(fresh, seed=12)
    scene.session.enable_ai = False
    scene.update(0.016)
    scene.draw(fresh.screen)

    palette = get_theme(theme)
    gap = settings.BOARD_MARGIN // 2
    middle = (scene.board_rect.bottom + scene.hand_rect.top) // 2

    strips = {
        'слева от поля': [(gap, y) for y in
                          range(scene.topbar.bottom + 20, settings.H - 20, 7)],
        'справа от панели': [(settings.W - 1 - gap, y) for y in
                             range(scene.topbar.bottom + 20, settings.H - 20, 7)],
        'между полем и рукой': [(x, middle) for x in
                                range(scene.board_rect.left + 30,
                                      scene.board_rect.right - 30, 9)],
        'снизу под рукой': [(x, settings.H - 1 - gap) for x in
                            range(scene.hand_rect.left + 30,
                                  scene.hand_rect.right - 30, 9)],
    }
    for name, points in strips.items():
        deviation = _median_deviation(palette, points, fresh.screen)
        assert deviation < 16, (
            f'{theme}/{name}: в зазоре не фон, а слой рамки ({deviation:.0f})'
        )


@pytest.mark.parametrize('theme', THEME_ORDER)
def test_menu_background_matches_the_gradient(app, theme):
    """Меню рисует фон целиком — ступеньки от рамки не должно быть и там."""
    fresh = App(theme=theme, headless=True)
    scene = MenuScene(fresh)
    scene.update(0.016)
    scene.draw(fresh.screen)

    # Меню рисует поверх фона только свои карточки, кайма остаётся чистой.
    points = []
    for depth in (1, 6, 11, 16, 21):
        for step in range(40, settings.W - 40, 60):
            points.append((step, depth))
            points.append((step, settings.H - 1 - depth))

    deviation = _median_deviation(get_theme(theme), points)
    assert deviation < 12, f'{theme}: в меню кайма не фон ({deviation:.0f})'


def test_background_is_full_window(app):
    """Фон совпадает с окном — никаких полей другого размера."""
    for theme in THEME_ORDER:
        background = render_background(get_theme(theme), (settings.W, settings.H))
        assert background.get_size() == (settings.W, settings.H)


def test_felt_pattern_draws_no_border(app):
    """Прямая проверка: функция сукна больше не рисует рамку."""
    from domino.ui.assets import _draw_felt_pattern

    size = (240, 160)
    surface = pg.Surface(size).convert()
    palette = get_theme('club_green')
    surface.fill(palette.bg_bottom)
    _draw_felt_pattern(surface, palette)

    # Внутри нет ни одного пикселя цвета прежней рамки.
    for color in ((86, 58, 32), (64, 42, 22)):
        for y in range(0, size[1], 3):
            for x in range(0, size[0], 3):
                pixel = surface.get_at((x, y))[:3]
                assert not all(abs(pixel[i] - color[i]) <= 6 for i in range(3)), (
                    f'найден цвет рамки {color} в ({x}, {y})'
                )
