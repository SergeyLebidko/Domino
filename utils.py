import pygame as pg
from settings import W, H, CELL_SIZE,  BACKGROUND_COLORS, LEFT_EDGE_PANE_COORDS, RIGHT_EDGE_PANE_COORDS, \
    STORAGE_PANE_COORDS, DOMINO_BACKSIDE_COLOR_1, DOMINO_BACKSIDE_COLOR_2, DOMINO_BORDER_COLOR, PLAYER_WIN, CMP_WIN,\
    STANDOFF


def get_player_pool_position(player_pool):
    """Функция возвращает положение пула домино игрока в окне игры"""

    return W // 2 - player_pool.PANE_WIDTH // 2, H - 4 * CELL_SIZE


def get_cmp_pool_position(cmp_pool):
    """Функция возвращает положение пула домино компьютера в окне игры"""

    return W // 2 - cmp_pool.PANE_WIDTH // 2, CELL_SIZE


def get_domino_backside():
    """Функция возвращает поверхность с отрисованной задней стороной домино"""

    surface = pg.Surface((CELL_SIZE, 2 * CELL_SIZE))

    # Заполняем фон
    surface.fill(DOMINO_BACKSIDE_COLOR_1)

    # Рисуем границу
    pg.draw.rect(surface, DOMINO_BORDER_COLOR, (0, 0, CELL_SIZE, CELL_SIZE * 2), 1)

    # Получем опорные величины
    delta_x = delta_y = CELL_SIZE // 6

    # Рисуем верхний и нижний квадраты
    pg.draw.rect(surface, DOMINO_BACKSIDE_COLOR_2, (delta_x, delta_y, 4 * delta_x, 4 * delta_y))
    pg.draw.rect(surface, DOMINO_BACKSIDE_COLOR_2, (delta_x, 7 * delta_y, 4 * delta_x, 4 * delta_y))

    # Рисуем разделительную линию
    pg.draw.line(surface, DOMINO_BACKSIDE_COLOR_2, (delta_x, 6 * delta_y), (5 * delta_x, 6 * delta_y), 3)

    return surface


def check_end_game(player_pool, cmp_pool, storage):
    """Функция проверяет условия окончания игры"""

    # Сторона, выложившая в цепочку все свои домино - побеждает
    if player_pool.is_empty:
        return PLAYER_WIN
    if cmp_pool.is_empty:
        return CMP_WIN

    # Если хранилище пусто и ни у кого нет доступных ходов - ничья
    if storage.is_empty and not is_available_moves(player_pool) and not is_available_moves(cmp_pool):
        return STANDOFF

    return None


def is_available_moves(pool):
    """Функция возвращает True, если из переданного пула возможен ход"""

    for pool_element in pool.pool:
        domino = pool_element['domino']
        available_for_left, available_for_right = check_available_for_domino(domino, pool.chain)
        if available_for_left or available_for_right:
            return True
    return False


def check_available_for_domino(domino, chain):
    """Для домино и цепочки функция возвращает кортеж (возможность хода влево, возможность хода вправо)"""

    available_for_left = domino.side1 == chain.left_side or domino.side2 == chain.left_side
    available_for_right = domino.side1 == chain.right_side or domino.side2 == chain.right_side
    return available_for_left, available_for_right


def draw_background(surface):
    """Функция отрисовывает фон окна игры"""

    step = 10
    for x in range(0, W + step, step):
        for y in range(0, H + step, step):
            color = BACKGROUND_COLORS[((x // step) + (y // step)) % 2]
            pg.draw.rect(surface, color, (x, y, step, step))


def draw_chain(surface, chain, scope):
    """Функция отрисовывает surface с цепочкой домино на surface окна"""

    if chain.width < W:
        scope.move_to_line(chain.center_line)
    chain.create_surface(scope)
    surface.blit(chain.surface, (0, 0))


def draw_edge_pane(surface, edge_pane):
    """Функция отрисовывает боковые панели на surface окна"""

    edge_pane.create_surfaces()
    surface.blit(edge_pane.left_surface, LEFT_EDGE_PANE_COORDS)
    surface.blit(edge_pane.right_surface, RIGHT_EDGE_PANE_COORDS)


def draw_storage_pane(surface, storage):
    """Функция отрисовывает панель с хранилищем на surface окна"""

    storage.create_surface()
    surface.blit(storage.surface, STORAGE_PANE_COORDS)


def draw_player_pool(surface, player_pool):
    """Функция отрисовывает пул игрока на surface окна"""

    player_pool.create_surface()
    x, y = get_player_pool_position(player_pool)
    surface.blit(player_pool.surface, (x, y))


def draw_cmp_pool(surface, cmp_pool):
    """Функция отрисовывает пул компьютера на surface окна"""

    cmp_pool.create_surface()
    x, y = get_cmp_pool_position(cmp_pool)
    surface.blit(cmp_pool.surface, (x, y))
