import pygame as pg
from settings import W, H, WINDOW_TITLE, FPS
from utils import draw_background, draw_chain
from classes import Domino, Chain, Scope


def main():

    # Инициализируем окно игры
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)

    # Создаем объект для ограничения FPS
    clock = pg.time.Clock()

    # Создаем объект для отображения выбранной части цепочки
    scope = Scope(- W // 2, W // 2)

    # Создаем тестовые домино
    domino_list = [Domino(side1, side2) for side1 in range(7) for side2 in range(side1, 7)]

    # Создаем тестовую цепочку
    import random
    chain = None
    random.shuffle(domino_list)
    while domino_list:
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
                    scope.move_left()
                if event.button == pg.BUTTON_WHEELUP:
                    scope.move_right()

        # Блок функций отрисовки
        draw_background(sc)

        # Отрисовка тестовой цепочки
        draw_chain(sc, chain, scope)

        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
