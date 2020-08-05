import pygame as pg
from settings import W, H, BACKGROUND_COLORS


def draw_background(surface):
    step = 10
    for x in range(0, W + step, step):
        for y in range(0, H + step, step):
            color = BACKGROUND_COLORS[((x // step) + (y // step)) % 2]
            pg.draw.rect(surface, color, (x, y, step, step))
