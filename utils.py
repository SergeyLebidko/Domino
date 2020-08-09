import pygame as pg
from settings import W, H, CELL_SIZE,  BACKGROUND_COLORS, LEFT_EDGE_PANE_COORDS, RIGHT_EDGE_PANE_COORDS, \
    STORAGE_PANE_COORDS


def get_player_pool_position(player_pool):
    return W // 2 - player_pool.PANE_WIDTH // 2, H - 4 * CELL_SIZE


def draw_background(surface):
    step = 10
    for x in range(0, W + step, step):
        for y in range(0, H + step, step):
            color = BACKGROUND_COLORS[((x // step) + (y // step)) % 2]
            pg.draw.rect(surface, color, (x, y, step, step))


def draw_chain(surface, chain, scope):
    if chain.width < scope.width:
        scope.move_to_line(chain.center_line)
    chain.create_surface(scope)
    surface.blit(chain.surface, (0, 0))


def draw_edge_pane(surface, edge_pane):
    edge_pane.create_surfaces()
    surface.blit(edge_pane.left_surface, LEFT_EDGE_PANE_COORDS)
    surface.blit(edge_pane.right_surface, RIGHT_EDGE_PANE_COORDS)


def draw_storage_pane(surface, storage):
    storage.create_surface()
    surface.blit(storage.surface, STORAGE_PANE_COORDS)


def draw_player_pool(surface, player_pool):
    player_pool.create_surface()
    x, y = get_player_pool_position(player_pool)
    surface.blit(player_pool.surface, (x, y))
