import random
import pygame as pg
from settings import W, H, WINDOW_TITLE, FPS, PLAYER_MOVE_MODE, CMP_MOVE_MODE, END_GAME_MODE
from utils import draw_background, draw_chain, draw_edge_pane, draw_storage_pane, draw_player_pool, draw_cmp_pool, \
    is_available_moves, is_quit_event, quit_game, check_end_game, draw_game_result
from classes import Domino, Chain, Scope, EdgePane, Storage, PlayerPool, CmpPool, Ai, ResultPane


def main():
    # Инициализируем окно игры
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)

    # Создаем объект для ограничения FPS
    clock = pg.time.Clock()

    # В данном цикле происходит инициализация новой игры
    while True:

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
        chain.add_first_domino(storage.take_domino())

        # Создаем и заполняем пул компьютера
        cmp_pool = CmpPool(chain)
        for _ in range(7):
            cmp_pool.add_domino(storage.take_domino())

        # Создаем объект для отображения крайних домино в цепочке
        edge_pane = EdgePane(chain, scope)

        # Создаем объект ИИ
        ai = Ai()

        # Создаем панель вывода результатов
        result_pane = ResultPane()

        # Выбираем первый режим работы - ход игрока
        next_mode = game_mode = PLAYER_MOVE_MODE

        # Основной цикл игры: в нем происходит отслеживание событий и чередование ходов
        resume_game = True
        while resume_game:

            # Проверяем событие закрытия окна
            events = pg.event.get()
            if is_quit_event(events):
                quit_game()

            # Если сейчас ход компьютера, то вызываем метод объекта ИИ
            if game_mode == CMP_MOVE_MODE:
                ai.next()
                game_result = check_end_game(player_pool, cmp_pool, storage)
                if game_result:
                    result_pane.set_game_result(game_result)
                    next_mode = END_GAME_MODE
                else:
                    next_mode = PLAYER_MOVE_MODE

            # Если сейчас ход игрока, то просматриваем клики по пулу игрока и хранилищу
            if game_mode == PLAYER_MOVE_MODE:
                storage_action = player_pool_action = False
                for event in events:
                    if event.type == pg.MOUSEBUTTONDOWN:
                        if event.button == pg.BUTTON_LEFT:
                            edge_pane.click(event.pos)
                            storage_action = storage.click(event.pos)
                            player_pool_action = player_pool.click(event.pos)

                    # Если игрок совершил действие (взял домино и/или положил его в цепочку), то передаем ход ИИ
                    if player_pool_action or (storage_action and not is_available_moves(player_pool)):
                        game_result = check_end_game(player_pool, cmp_pool, storage)
                        if game_result:
                            result_pane.set_game_result(game_result)
                            next_mode = END_GAME_MODE
                        else:
                            next_mode = CMP_MOVE_MODE

            # Если игра завершена, то выводися результат и запрашивается дальнейшее дествие: играть ещё или выйти
            if game_mode == END_GAME_MODE:
                for event in events:
                    if event.type == pg.KEYDOWN:
                        if event.key == pg.K_ESCAPE:
                            quit_game()
                        if event.key == pg.K_KP_ENTER or event.key == 13:
                            resume_game = False
                            break

            # Независимо от текущего режима обрабатываем перемещение по цепочке
            for event in events:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_LEFT:
                        scope.move_to_left()
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_RIGHT:
                        scope.move_to_right()

                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == pg.BUTTON_WHEELDOWN:
                        scope.step_left()
                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == pg.BUTTON_WHEELUP:
                        scope.step_right()

            # Блок функций отрисовки
            draw_background(sc)
            draw_chain(sc, chain, scope)
            draw_edge_pane(sc, edge_pane)
            draw_storage_pane(sc, storage)
            draw_player_pool(sc, player_pool)
            draw_cmp_pool(sc, cmp_pool)
            draw_game_result(sc, result_pane)
            pg.display.update()

            clock.tick(FPS)

            game_mode = next_mode


if __name__ == '__main__':
    main()
