import random
import pygame as pg
from settings import W, H, WINDOW_TITLE, FPS, PLAYER_MOVE_MODE, CMP_MOVE_MODE, END_GAME_MODE
from utils import draw_background, draw_chain, draw_edge_pane, draw_storage_pane, draw_player_pool, draw_cmp_pool
from classes import Domino, Chain, Scope, EdgePane, Storage, PlayerPool, CmpPool, Ai


def main():
    # Инициализируем окно игры
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)

    # Создаем объект для ограничения FPS
    clock = pg.time.Clock()

    # Создаем пустую цепочку
    chain = Chain()

    # Создаем объект для представления области просмотра
    scope = Scope(chain)

    # Создаем пул домино игрока
    # chain - цепочка, в которую будут добавляться домино из пула
    # scope - область просмотра для быстрого отображения края цепочки при ходе игрока
    player_pool = PlayerPool(chain, scope)

    # Создаем хранилище
    # player_pool - пул домино игрока, в которые будут передаваться домино при клике на значке хранилища
    storage = Storage(player_pool)

    # Заполняем пул игрока случайными домино
    for _ in range(7):
        player_pool.add_domino(storage.take_domino())

    # Выбираем и добавляем первое домино в цепочку
    first_domino = storage.take_domino()
    if first_domino.is_double:
        first_domino.rotate(Domino.UP_ORIENTATION)
    else:
        first_domino.rotate(random.choice(Domino.HORIZONTAL_ORIENTATION))
    chain.add_first_domino(first_domino)

    # Создаем и заполняем пул компьютера
    cmp_pool = CmpPool()
    for _ in range(7):
        cmp_pool.add_domino(storage.take_domino())

    # Создаем объект для отображения крайних домино в цепочке
    edge_pane = EdgePane(chain, scope)

    # Создаем объект ИИ
    ai = Ai()

    # Выбираем первый режим игры - ход игрока
    game_mode = PLAYER_MOVE_MODE

    storage_action = player_pool_action = False

    while True:
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

            # Если сейчас ход компьютера, то вызываем метод объекта ИИ
            if game_mode == CMP_MOVE_MODE:
                ai.next()
                storage_action = player_pool_action = False
                game_mode = PLAYER_MOVE_MODE

            # Если сейчас ход игрока, то просматриваем события мыши и клавиатуры
            if game_mode == PLAYER_MOVE_MODE:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_LEFT:
                        scope.move_to_left()
                    if event.key == pg.K_RIGHT:
                        scope.move_to_right()

                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == pg.BUTTON_LEFT:
                        edge_pane.click(event.pos)
                        storage_action = storage.click(event.pos)
                        player_pool_action = player_pool.click(event.pos)
                    if event.button == pg.BUTTON_WHEELDOWN:
                        scope.step_left()
                    if event.button == pg.BUTTON_WHEELUP:
                        scope.step_right()

                # Если игрок совершил действие (взял домино и/или положил его в цепочку), то передаем ход ИИ
                if player_pool_action or (storage_action and not player_pool.is_available_moves):
                    game_mode = CMP_MOVE_MODE

        # Блок функций отрисовки
        draw_background(sc)
        draw_chain(sc, chain, scope)
        draw_edge_pane(sc, edge_pane)
        draw_storage_pane(sc, storage)
        draw_player_pool(sc, player_pool)
        draw_cmp_pool(sc, cmp_pool)

        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
