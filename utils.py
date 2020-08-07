import pygame as pg
from settings import W, H, BACKGROUND_COLORS, CELL_SIZE, LEFT_EDGE_PANE_COORDS, RIGHT_EDGE_PANE_COORDS


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
