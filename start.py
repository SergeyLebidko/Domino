import pygame as pg
from settings import W, H, WINDOW_TITLE, FPS
from utils import draw_background
from classes import Domino


def main():

    # Инициализируем окно игры
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)

    # Создаем объект для ограничения FPS
    clock = pg.time.Clock()

    # Создаем тестовый домино
    domino = Domino(5, 6)

    while True:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_LEFT:
                    pass
                if event.button == pg.BUTTON_WHEELDOWN:
                    pass
                if event.button == pg.BUTTON_WHEELUP:
                    pass

        # Блок функций отрисовки
        draw_background(sc)

        # Отрисовка тестового домино
        sc.blit(domino.surface, (100, 100))

        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
