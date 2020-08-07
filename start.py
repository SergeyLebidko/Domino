import pygame as pg
from settings import W, H, WINDOW_TITLE, FPS
from utils import draw_background, draw_chain, draw_edge_pane
from classes import Domino, Chain, Scope, EdgePane


def main():
    # Инициализируем окно игры
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)

    # Создаем объект для ограничения FPS
    clock = pg.time.Clock()

    # Создаем тестовые домино
    domino_list = [Domino(side1, side2) for side1 in range(7) for side2 in range(side1, 7)]

    # Создаем тестовую цепочку
    import random
    chain = None
    random.shuffle(domino_list)
    count = 0
    while domino_list and count < 29:
        domino = domino_list.pop()
        if domino.is_double:
            domino.rotate(random.choice(Domino.VERTICAL_ORIENTATIONS))
        else:
            domino.rotate(random.choice(Domino.HORIZONTAL_ORIENTATION))
        if not chain:
            chain = Chain(domino)
        else:
            if random.choice([True, False]):
                chain.add_to_right(domino)
            else:
                chain.add_to_left(domino)
        count += 1

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
                    pass
                if event.button == pg.BUTTON_WHEELDOWN:
                    scope.step_left(chain)
                if event.button == pg.BUTTON_WHEELUP:
                    scope.step_right(chain)

        # Блок функций отрисовки
        draw_background(sc)

        # Отрисовка цепочки
        draw_chain(sc, chain, scope)

        # Отрисовка панлей с крайними домино
        draw_edge_pane(sc, edge_pane)

        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
