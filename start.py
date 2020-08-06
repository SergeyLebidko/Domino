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

    # Создаем тестовые домино
    domino_list = [Domino(side1, side2) for side1 in range(7) for side2 in range(side1, 7)]

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

        # Отрисовка тестовых домино
        x0, y0 = 10, 10
        for domino in domino_list:
            sc.blit(domino.surface, (x0, y0))
            if domino.side2 == 6:
                x0, y0 = 10, y0 + 70
            else:
                x0 += 130

        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
