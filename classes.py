import random
import pygame as pg
from collections import namedtuple
from settings import W, H, CELL_SIZE, DOMINO_BACKGROUND_COLOR, DOMINO_BORDER_COLOR, DOMINO_DOT_COLOR, \
    LEFT_EDGE_PANE_COORDS, RIGHT_EDGE_PANE_COORDS, TRANSPARENT_COLOR, STORAGE_PANE_COORDS, POOL_DOMINO_INTERVAL, \
    PLAYER_WIN, CMP_WIN, RESULT_BACKGROUND_COLORS, LABEL_COLORS, PLAYER_LABEL, CMP_LABEL
from utils import get_player_pool_position, get_domino_backside, is_available_moves, check_available_for_domino

ChainElement = namedtuple('ChainElement', ['rect', 'domino', 'label'])


class EdgePane:

    def __init__(self, chain, scope):
        self.chain, self.scope = chain, scope
        self.left_surface = pg.Surface((2 * CELL_SIZE, 2 * CELL_SIZE))
        self.left_surface.set_colorkey(TRANSPARENT_COLOR)
        self.left_surface.set_alpha(100)
        self.right_surface = pg.Surface((2 * CELL_SIZE, 2 * CELL_SIZE))
        self.right_surface.set_colorkey(TRANSPARENT_COLOR)
        self.right_surface.set_alpha(100)

    def create_surfaces(self):
        self.left_surface.fill(TRANSPARENT_COLOR)
        self.right_surface.fill(TRANSPARENT_COLOR)

        data = [
            (
                self.left_surface,
                self.chain.left_domino,
                self.scope.left_line - self.chain.left_line
            ),
            (
                self.right_surface,
                self.chain.right_domino,
                self.chain.right_line - self.scope.right_line
            )
        ]

        for surface, domino, delta in data:
            surface.fill(TRANSPARENT_COLOR)
            if delta > domino.width:
                domino_rect = self.create_domino_rect(domino)
                surface.blit(domino.surface, domino_rect)

    @staticmethod
    def create_domino_rect(domino):
        x, y = CELL_SIZE - domino.width // 2, CELL_SIZE - domino.height // 2
        return pg.Rect(x, y, domino.width, domino.height)

    def click(self, pos):
        left_domino_rect = self.create_domino_rect(self.chain.left_domino)
        left_domino_rect.x = LEFT_EDGE_PANE_COORDS[0] + left_domino_rect.x
        left_domino_rect.y = LEFT_EDGE_PANE_COORDS[1] + left_domino_rect.y

        right_domino_rect = self.create_domino_rect(self.chain.right_domino)
        right_domino_rect.x = RIGHT_EDGE_PANE_COORDS[0] + right_domino_rect.x
        right_domino_rect.y = RIGHT_EDGE_PANE_COORDS[1] + right_domino_rect.y

        if left_domino_rect.collidepoint(pos):
            self.scope.move_to_left()
        if right_domino_rect.collidepoint(pos):
            self.scope.move_to_right()


class Scope:
    SCROLL_STEP = 40
    SCROLL_LIMIT = 3 * CELL_SIZE

    def __init__(self, chain):
        self.chain = chain
        self.left_line, self.right_line = None, None
        self.move_to_line(chain.center_line)

    def step_left(self):
        left_limit = self.chain.left_line - self.SCROLL_LIMIT
        if self.left_line >= left_limit:
            self.left_line -= self.SCROLL_STEP
            self.right_line -= self.SCROLL_STEP
        if self.left_line < left_limit:
            self.move_to_left()

    def step_right(self):
        right_limit = self.chain.right_line + self.SCROLL_LIMIT
        if self.right_line <= right_limit:
            self.left_line += self.SCROLL_STEP
            self.right_line += self.SCROLL_STEP
        if self.right_line > right_limit:
            self.move_to_right()

    def move_to_left(self):
        self.left_line = self.chain.left_line - self.SCROLL_LIMIT
        self.right_line = self.left_line + W

    def move_to_right(self):
        self.right_line = self.chain.right_line + self.SCROLL_LIMIT
        self.left_line = self.right_line - W

    def move_to_line(self, line):
        self.left_line, self.right_line = line - W // 2, line + W // 2

    def rect_in_scope(self, rect):
        return (self.left_line <= rect.left <= self.right_line) or (self.left_line <= rect.right <= self.right_line)


class Domino:
    RIGHT_ORIENTATION = 1
    DOWN_ORIENTATION = 2
    LEFT_ORIENTATION = 3
    UP_ORIENTATION = 4

    VERTICAL_ORIENTATIONS = UP_ORIENTATION, DOWN_ORIENTATION
    HORIZONTAL_ORIENTATION = LEFT_ORIENTATION, RIGHT_ORIENTATION

    dot_data = {
        0: [],
        1: [(0, 0)],
        2: [(-2, -2), (2, 2)],
        3: [(-2, -2), (0, 0), (2, 2)],
        4: [(-2, 2), (2, 2), (2, -2), (-2, -2)],
        5: [(-2, 2), (2, 2), (0, 0), (2, -2), (-2, -2)],
        6: [(-2, 2), (0, 2), (2, 2), (2, -2), (0, -2), (-2, -2)]
    }

    def __init__(self, side1, side2):
        self.side1, self.side2 = side1, side2
        self.corner_points, self.dot_coords, self.separator_coords = self.create_coords()
        self.surface = self.create_surface()
        self.rect = self.create_rect()
        self.orientation = self.RIGHT_ORIENTATION

    def create_coords(self):
        # Формируем опорные величины
        dx, dy = CELL_SIZE // 6, CELL_SIZE // 6
        left_x0, left_y0 = - (dx * 3), 0
        right_x0, right_y0 = dx * 3, 0

        # Формируем угловые точки
        x1, y1 = - CELL_SIZE, CELL_SIZE // 2
        x2, y2 = CELL_SIZE, - CELL_SIZE // 2

        # Формируем список точек на домино
        dot_coords = []
        for x0, y0, side in [(left_x0, left_y0, self.side1), (right_x0, right_y0, self.side2)]:
            for dot_x, dot_y in self.dot_data[side]:
                dot_coords.append((x0 + dot_x * dx, y0 + dot_y * dy))

        # Формируем координаты разделительной линии
        separator_x1, separator_y1 = 0, dy * 2
        separator_x2, separator_y2 = 0, - (dy * 2)

        return [(x1, y1), (x2, y2)], dot_coords, [(separator_x1, separator_y1), (separator_x2, separator_y2)]

    def create_surface(self):
        # Формируем опорные величины
        x1 = min(self.corner_points[0][0], self.corner_points[1][0])
        y1 = max(self.corner_points[0][1], self.corner_points[1][1])
        x2 = max(self.corner_points[0][0], self.corner_points[1][0])
        y2 = min(self.corner_points[0][1], self.corner_points[1][1])
        width, height = abs(x1 - x2), abs(y1 - y2)
        x0, y0 = width // 2, height // 2

        surface = pg.Surface((width, height))

        # Рисуем фон домино
        surface.fill(DOMINO_BACKGROUND_COLOR)

        # Рисуем границу домино
        pg.draw.rect(surface, DOMINO_BORDER_COLOR, (x0 + x1, y0 - y1, width, height), 1)

        # Рисуем разделитель между половинками домино
        separator_x1, separator_y1 = self.separator_coords[0]
        separator_x2, separator_y2 = self.separator_coords[1]
        pg.draw.line(
            surface,
            DOMINO_BORDER_COLOR,
            (x0 + separator_x1, y0 - separator_y1),
            (x0 + separator_x2, y0 - separator_y2),
            1
        )

        # Рисуем точки на домино
        for dot_x, dot_y in self.dot_coords:
            pg.draw.circle(surface, DOMINO_DOT_COLOR, (x0 + dot_x, y0 - dot_y), CELL_SIZE // 6 // 2)

        return surface

    def create_rect(self):
        return pg.Rect(
            - self.surface.get_width() // 2,
            self.surface.get_height() // 2,
            self.surface.get_width(),
            self.surface.get_height()
        )

    def rotate(self, new_orientation):
        if new_orientation == self.orientation:
            return
        if new_orientation > self.orientation:
            rotate_count = new_orientation - self.orientation
        else:
            rotate_count = new_orientation + 4 - self.orientation

        for _ in range(rotate_count):
            # Поворачиваем угловые точки
            x1, y1 = self.corner_points[0]
            x2, y2 = self.corner_points[1]
            self.corner_points[0] = - y1, x1
            self.corner_points[1] = - y2, x2

            # Поворачиваем координаты разделительной линии
            separator_x1, separator_y1 = self.separator_coords[0]
            separator_x2, separator_y2 = self.separator_coords[1]
            self.separator_coords[0] = - separator_y1, separator_x1
            self.separator_coords[1] = - separator_y2, separator_x2

            # Поворачиваем точки на половинках домино
            self.dot_coords = [(- dot_y, dot_x) for dot_x, dot_y in self.dot_coords]

        self.surface = self.create_surface()
        self.rect = self.create_rect()
        self.orientation = new_orientation

    @property
    def is_double(self):
        return self.side1 == self.side2

    @property
    def is_right_orientation(self):
        return self.orientation == self.RIGHT_ORIENTATION

    @property
    def is_left_orientation(self):
        return self.orientation == self.LEFT_ORIENTATION

    @property
    def width(self):
        return self.rect.width

    @property
    def height(self):
        return self.rect.height

    def __str__(self):
        if self.orientation == self.RIGHT_ORIENTATION:
            res = f'[{self.side1}:{self.side2}]'
        else:
            res = f'[{self.side2}:{self.side1}]'
        return res


class Chain:

    def __init__(self):
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey(TRANSPARENT_COLOR)

        self.domino_list = []
        self.left_line, self.right_line = None, None
        self.left_side, self.right_side = None, None

    def add_first_domino(self, domino):
        if domino.is_double:
            domino.rotate(Domino.UP_ORIENTATION)
        else:
            domino.rotate(random.choice(Domino.HORIZONTAL_ORIENTATION))

        domino_rect = domino.rect
        self.domino_list.append(ChainElement(domino_rect, domino, None))
        self.left_line, self.right_line = domino_rect.left, domino_rect.right

        if domino.is_double:
            self.left_side, self.right_side = domino.side1, domino.side2
        else:
            if domino.is_right_orientation:
                self.left_side, self.right_side = domino.side1, domino.side2
            if domino.is_left_orientation:
                self.left_side, self.right_side = domino.side2, domino.side1

    def add_to_right(self, domino, label):
        if not self.domino_list:
            self.add_first_domino(domino)
            return

        # Проверка возможности добавления домино в правую часть цепочки
        if domino.side1 != self.right_side and domino.side2 != self.right_side:
            raise Exception('Некорректное добавление справа')

        # Ориентируем домино
        if domino.is_double:
            domino.rotate(Domino.UP_ORIENTATION)
        else:
            if domino.side1 == self.right_side:
                domino.rotate(Domino.RIGHT_ORIENTATION)
                self.right_side = domino.side2
            elif domino.side2 == self.right_side:
                domino.rotate(Domino.LEFT_ORIENTATION)
                self.right_side = domino.side1

        domino_rect = domino.rect
        domino_rect = pg.Rect(
            self.right_line + 2,
            domino_rect.y,
            domino_rect.width,
            domino_rect.height
        )
        self.domino_list.append(ChainElement(domino_rect, domino, label))
        self.right_line = domino_rect.right

    def add_to_left(self, domino, label):
        if not self.domino_list:
            self.add_first_domino(domino)
            return

        # Проверка возможности добавления домино в левую часть цепочки
        if domino.side1 != self.left_side and domino.side2 != self.left_side:
            raise Exception('Некорректное добавление слева')

        if domino.is_double:
            domino.rotate(Domino.UP_ORIENTATION)
        else:
            if domino.side1 == self.left_side:
                domino.rotate(Domino.LEFT_ORIENTATION)
                self.left_side = domino.side2
            elif domino.side2 == self.left_side:
                domino.rotate(Domino.RIGHT_ORIENTATION)
                self.left_side = domino.side1

        domino_rect = domino.rect
        domino_rect = pg.Rect(
            self.left_line - 2 - domino_rect.width,
            domino_rect.y,
            domino_rect.width,
            domino_rect.height
        )
        self.domino_list.insert(0, ChainElement(domino_rect, domino, label))
        self.left_line = domino_rect.left

    def create_surface(self, scope):
        self.surface.fill(TRANSPARENT_COLOR)
        scope_domino_list = [
            (rect, domino, label) for rect, domino, label in self.domino_list if scope.rect_in_scope(rect)
        ]
        for rect, domino, label in scope_domino_list:
            self.surface.blit(domino.surface, (rect.x - scope.left_line, H // 2 - rect.y))
            if label:
                pg.draw.line(
                    self.surface,
                    LABEL_COLORS[label],
                    (rect.left - scope.left_line + 5, H // 2 + rect.height // 2 + 5),
                    (rect.right - scope.left_line - 5, H // 2 + rect.height // 2 + 5),
                    3
                )

    @property
    def width(self):
        return self.right_line - self.left_line

    @property
    def center_line(self):
        if not self.domino_list:
            return 0
        return (self.left_line + self.right_line) // 2

    @property
    def left_domino(self):
        _, domino, _ = self.domino_list[0]
        return domino

    @property
    def right_domino(self):
        _, domino, _ = self.domino_list[-1]
        return domino


class Storage:
    BACKGROUND_COLOR_1 = (224, 207, 177)
    BACKGROUND_COLOR_2 = (255, 229, 180)
    CIRCLE_COLOR = (50, 150, 0)
    FONT_COLOR = (255, 255, 255)

    def __init__(self, player_pool, logger):
        self.player_pool, self.logger = player_pool, logger
        self.domino_list = [Domino(side1, side2) for side1 in range(7) for side2 in range(side1, 7)]
        random.shuffle(self.domino_list)
        self.surface = pg.Surface((CELL_SIZE * 2, CELL_SIZE * 3))
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.font = pg.font.Font(None, 24)

    def create_surface(self):
        self.surface.fill(TRANSPARENT_COLOR)
        if not self.storage_size:
            return

        backside_surface = get_domino_backside()
        self.surface.blit(backside_surface, (CELL_SIZE // 2, CELL_SIZE // 2))

        # Рисуем область вывода количества домино в хранилище
        pg.draw.circle(self.surface, self.CIRCLE_COLOR, (3 * CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3)
        font_surface = self.font.render(str(self.storage_size), 1, self.FONT_COLOR)
        font_rect = font_surface.get_rect()

        self.surface.blit(font_surface,
                          (3 * CELL_SIZE // 2 - font_rect.width // 2, CELL_SIZE // 2 - font_rect.height // 2))

    @property
    def storage_size(self):
        return len(self.domino_list)

    @property
    def is_empty(self):
        return len(self.domino_list) == 0

    def take_domino(self):
        return self.domino_list.pop()

    def click(self, pos):
        if not self.storage_size or is_available_moves(self.player_pool):
            return False

        click_x = pos[0] - STORAGE_PANE_COORDS[0] - CELL_SIZE // 2
        click_y = pos[1] - STORAGE_PANE_COORDS[1] - CELL_SIZE // 2
        domino_rect = pg.Rect(0, 0, CELL_SIZE, 2 * CELL_SIZE)
        if domino_rect.collidepoint(click_x, click_y):
            domino = self.domino_list.pop()
            self.player_pool.add_domino(domino)
            self.logger.add_to_log('Игрок взял из кучи...')
            return True

        return False


class PlayerPool:
    PANE_WIDTH = W - 2 * CELL_SIZE
    PANE_HEIGHT = 3 * CELL_SIZE

    TO_LEFT_BUTTON_COORDS = ((1, 2), (3, 1), (3, 3))
    TO_RIGHT_BUTTON_COORDS = ((1, 1), (3, 2), (1, 3))

    ARROW_COLOR = (255, 255, 255)

    def __init__(self, chain, scope, logger):
        self.pool = []
        self.chain, self.scope, self.logger = chain, scope, logger
        self.surface = pg.Surface((self.PANE_WIDTH, self.PANE_HEIGHT))
        self.surface.set_colorkey(TRANSPARENT_COLOR)

    def create_surface(self):
        self.surface.fill(TRANSPARENT_COLOR)

        if not self.pool:
            return

        # Отрисовываем домино из пула
        domino_block_width = POOL_DOMINO_INTERVAL * self.pool_size
        block_x0, block_y0 = self.PANE_WIDTH // 2 - domino_block_width // 2, CELL_SIZE
        for number, pool_element in enumerate(self.pool, 0):
            domino = pool_element['domino']
            domino_rect = pg.Rect(block_x0 + number * POOL_DOMINO_INTERVAL, block_y0, CELL_SIZE, 2 * CELL_SIZE)
            pool_element['rect'] = domino_rect
            self.surface.blit(domino.surface, domino_rect)

            # Проверяем доступность ходов для домино
            available_for_left, available_for_right = check_available_for_domino(domino, self.chain)

            # Проверяем возможность добавления влево и рисуем стрелку
            delta_x = delta_y = CELL_SIZE // 8
            if available_for_left:
                x0, y0 = domino_rect.x, domino.rect.y - CELL_SIZE // 2
                arrow_coords = [(x0 + delta_x * x, y0 + delta_y * y) for x, y in self.TO_LEFT_BUTTON_COORDS]
                pg.draw.polygon(self.surface, self.ARROW_COLOR, arrow_coords)
                pool_element['append_to_left_rect'] = pg.Rect(x0, y0, CELL_SIZE // 2, CELL_SIZE // 2)
            else:
                pool_element['append_to_left_rect'] = None

            # Проверяем возможность добавления вправо и рисуем стрелку
            if available_for_right:
                x0, y0 = domino_rect.x + CELL_SIZE // 2, domino.rect.y - CELL_SIZE // 2
                arrow_coords = [(x0 + delta_x * x, y0 + delta_y * y) for x, y in self.TO_RIGHT_BUTTON_COORDS]
                pg.draw.polygon(self.surface, self.ARROW_COLOR, arrow_coords)
                pool_element['append_to_right_rect'] = pg.Rect(x0, y0, CELL_SIZE // 2, CELL_SIZE // 2)
            else:
                pool_element['append_to_right_rect'] = None

    @property
    def pool_size(self):
        return len(self.pool)

    @property
    def is_empty(self):
        return len(self.pool) == 0

    @property
    def domino_list(self):
        return [pool_element['domino'] for pool_element in self.pool]

    def add_domino(self, domino):
        domino.rotate(Domino.UP_ORIENTATION)
        self.pool.append(
            {
                'rect': None,
                'append_to_left_rect': None,
                'append_to_right_rect': None,
                'domino': domino
            }
        )

    def click(self, pos):
        pane_x, pane_y = get_player_pool_position(self)
        click_x, click_y = pos[0] - pane_x, pos[1] - pane_y

        pane_rect = self.surface.get_rect()
        if not pane_rect.collidepoint(click_x, click_y):
            return False

        for pool_element in self.pool:
            left_arrow_rect = pool_element['append_to_left_rect']
            right_arrow_rect = pool_element['append_to_right_rect']
            domino = pool_element['domino']

            # Обрабатываем добавление домино в левую часть цепочки
            if left_arrow_rect and left_arrow_rect.collidepoint(click_x, click_y):
                self.chain.add_to_left(domino, PLAYER_LABEL)
                self.logger.add_to_log(f'Игрок походил влево {domino}')
                self.scope.move_to_left()
                break

            # Обрабатываем добавление домино в правую часть цепочки
            if right_arrow_rect and right_arrow_rect.collidepoint(click_x, click_y):
                self.chain.add_to_right(domino, PLAYER_LABEL)
                self.logger.add_to_log(f'Игрок походил вправо {domino}')
                self.scope.move_to_right()
                break
        else:
            return False

        self.pool.remove(pool_element)
        return True


class CmpPool:
    PANE_WIDTH = W - 2 * CELL_SIZE
    PANE_HEIGHT = 3 * CELL_SIZE

    def __init__(self, chain):
        self.pool = []
        self.chain = chain
        self.surface = pg.Surface((self.PANE_WIDTH, self.PANE_HEIGHT))
        self.surface.set_colorkey(TRANSPARENT_COLOR)

    def create_surface(self):
        self.surface.fill(TRANSPARENT_COLOR)

        if not self.pool:
            return

        domino_block_width = POOL_DOMINO_INTERVAL * self.pool_size
        block_x0, block_y0 = self.PANE_WIDTH // 2 - domino_block_width // 2, CELL_SIZE
        domino_backside = get_domino_backside()
        for index in range(self.pool_size):
            self.surface.blit(domino_backside, (block_x0 + index * POOL_DOMINO_INTERVAL, block_y0))

    def add_domino(self, domino):
        self.pool.append(domino)

    def remove_domino(self, domino):
        self.domino_list.remove(domino)

    @property
    def pool_size(self):
        return len(self.pool)

    @property
    def is_empty(self):
        return len(self.pool) == 0

    @property
    def domino_list(self):
        return self.pool


class ResultPane:
    FONT_COLOR = (20, 20, 20)

    def __init__(self):
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.game_result = None
        self.create_surface()

    def set_game_result(self, game_result):
        self.game_result = game_result
        self.create_surface()

    def create_surface(self):
        self.surface.fill(TRANSPARENT_COLOR)
        if not self.game_result:
            return

        if self.game_result == PLAYER_WIN:
            msg = 'Вы победили!'
        elif self.game_result == CMP_WIN:
            msg = 'Вы проиграли...'
        else:
            msg = 'Ничья'

        delta = CELL_SIZE // 4
        x1, y1 = W // 2 - delta * 15, H // 2 - delta * 5
        x2, y2 = W // 2 + delta * 15, H // 2 + delta * 5
        for x in range(x1, x2, delta):
            for y in range(y1, y2, delta):
                pg.draw.rect(
                    self.surface,
                    RESULT_BACKGROUND_COLORS[(x // delta + y // delta) % 2],
                    (x, y, delta, delta)
                )
        pg.draw.rect(self.surface, DOMINO_BORDER_COLOR, (x1, y1, x2 - x1, y2 - y1), 1)

        font_result = pg.font.Font(None, 36)
        font_resume = pg.font.Font(None, 24)
        result_surface = font_result.render(msg, 1, self.FONT_COLOR)
        resume_surface = font_resume.render('[Enter] - Играть еще раз. [ESC] - Выход...', 1, self.FONT_COLOR)

        result_rect = result_surface.get_rect()
        self.surface.blit(
            result_surface,
            (W // 2 - result_rect.width // 2, H // 2 - result_rect.height - 2)
        )
        resume_rect = resume_surface.get_rect()
        self.surface.blit(
            resume_surface,
            (W // 2 - resume_rect.width // 2, H // 2 + result_rect.height)
        )


class Logger:
    FONT_COLOR = (255, 255, 255)
    MSG_DISPLAY_LIMIT = 7

    def __init__(self):
        self.log = []
        self.surface = pg.Surface((W, H))
        self.surface.set_alpha(150)
        self.surface.set_colorkey(TRANSPARENT_COLOR)

    def create_surface(self):
        self.surface.fill(TRANSPARENT_COLOR)
        if not self.log:
            return

        font = pg.font.Font(None, 32)

        line = 10
        for rec in self.log[-self.MSG_DISPLAY_LIMIT:]:
            font_surface = font.render(rec, 0, self.FONT_COLOR)
            self.surface.blit(font_surface, (10, line))
            line += font_surface.get_rect().height

    def add_to_log(self, rec):
        self.log.append(rec)


class Ai:

    def __init__(self, chain, cmp_pool, storage, scope, logger):
        self.chain, self.cmp_pool, self.storage, self.scope, self.logger = chain, cmp_pool, storage, scope, logger

    def next(self):

        # Формируем список доступных ходов для пула компьютера
        moves_list = []

        for domino in self.cmp_pool.domino_list:
            moves = self.get_moves_for_domino(domino)
            moves_list.extend(moves)

        # Если нет доступных ходов, то пытаемся взять домино из хранилища
        if not moves_list and not self.storage.is_empty:
            domino = self.storage.take_domino()
            self.logger.add_to_log('Компьютер взял из кучи...')
            self.cmp_pool.add_domino(domino)
            moves = self.get_moves_for_domino(domino)
            moves_list.extend(moves)

        # Если и после этого нет доступных ходов - просто выходим
        if not moves_list:
            return

        # Выбираем случайный ход
        move = random.choice(moves_list)

        # Применяем выбранный ход
        domino = move['domino']
        direction = move['direction']
        self.cmp_pool.remove_domino(domino)
        if direction == 'left':
            self.chain.add_to_left(domino, CMP_LABEL)
            self.logger.add_to_log(f'Компьютер походил влево {domino}')
            self.scope.move_to_left()
        if direction == 'right':
            self.chain.add_to_right(domino, CMP_LABEL)
            self.logger.add_to_log(f'Компьютер походил вправо {domino}')
            self.scope.move_to_right()

    def get_moves_for_domino(self, domino):
        moves = []
        available_for_left, available_for_right = check_available_for_domino(domino, self.chain)
        if available_for_left:
            moves.append({'direction': 'left', 'domino': domino})
        if available_for_right:
            moves.append({'direction': 'right', 'domino': domino})
        return moves
