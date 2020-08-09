import random
import pygame as pg
from settings import W, H, WINDOW_TITLE, FPS
from utils import draw_background, draw_chain, draw_edge_pane, draw_storage_pane
from classes import Domino, Chain, Scope, EdgePane, Storage


def main():
    # Инициализируем окно игры
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)

    # Создаем объект для ограничения FPS
    clock = pg.time.Clock()

    # Созоаем хранилище
    storage = Storage()

    # Создаем цепочку
    start_domino = storage.take_domino()
    if start_domino.is_double:
        start_domino.rotate(Domino.UP_ORIENTATION)
    else:
        start_domino.rotate(random.choice(Domino.HORIZONTAL_ORIENTATION))
    chain = Chain(start_domino)

    # Создаем объект для отображения выбранной части цепочки и центрируем его по цепочке
    scope = Scope(- W // 2, W // 2)
    scope.move_to_line(chain.center_line)

    # Создаем объект для отображения крайних домино в цепочке, если они в данный момент не видимы
    edge_pane = EdgePane(chain, scope)

    while True:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_LEFT:
                    scope.move_to_left(chain)
                if event.key == pg.K_RIGHT:
                    scope.move_to_right(chain)

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_LEFT:
                    storage.click(event.pos)
                    edge_pane.click(event.pos)
                if event.button == pg.BUTTON_WHEELDOWN:
                    scope.step_left(chain)
                if event.button == pg.BUTTON_WHEELUP:
                    scope.step_right(chain)

        # Блок функций отрисовки
        draw_background(sc)

        # Отрисовка цепочки
        draw_chain(sc, chain, scope)

        # Отрисовка панелей с крайними домино
        draw_edge_pane(sc, edge_pane)

        # Отрисовка панели с хранилищем
        draw_storage_pane(sc, storage)

        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
