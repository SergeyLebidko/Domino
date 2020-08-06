import pygame as pg
from collections import namedtuple
from settings import W, H, CELL_SIZE, DOMINO_BACKGROUND_COLOR, DOMINO_BORDER_COLOR, DOMINO_DOT_COLOR

ChainElement = namedtuple('ChainElement', ['rect', 'domino'])


class Scope:

    SCROLL_STEP = 50
    SCROLL_LIMIT = 3 * CELL_SIZE

    def __init__(self, left_line, right_line):
        self.left_line, self.right_line = left_line, right_line
        self.width = right_line - left_line

    def step_left(self, chain):
        left_limit = chain.left_line - self.SCROLL_LIMIT
        if self.left_line >= left_limit:
            self.left_line -= self.SCROLL_STEP
            self.right_line -= self.SCROLL_STEP
        if self.left_line < left_limit:
            self.move_to_left(chain)

    def step_right(self, chain):
        right_limit = chain.right_line + self.SCROLL_LIMIT
        if self.right_line <= right_limit:
            self.left_line += self.SCROLL_STEP
            self.right_line += self.SCROLL_STEP
        if self.right_line > right_limit:
            self.move_to_right(chain)

    def move_to_left(self, chain):
        self.left_line = chain.left_line - self.SCROLL_LIMIT
        self.right_line = self.left_line + self.width

    def move_to_right(self, chain):
        self.right_line = chain.right_line + self.SCROLL_LIMIT
        self.left_line = self.right_line - self.width

    def move_to_line(self, line):
        self.left_line, self.right_line = line - self.width // 2, line + self.width // 2

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
        rotate_count = max(new_orientation, self.orientation) - min(new_orientation, self.orientation)
        if not rotate_count:
            return
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


class Chain:

    TRANSPARENT_COLOR = (255, 0, 0)

    def __init__(self, domino):
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey(self.TRANSPARENT_COLOR)

        self.domino_list = []

        domino_rect = domino.rect
        self.domino_list.append(ChainElement(domino_rect, domino))
        self.left_line, self.right_line = domino_rect.left, domino_rect.right

        if domino.is_double:
            self.left_side, self.right_side = domino.side1, domino.side2
        else:
            if domino.is_right_orientation:
                self.left_side, self.right_side = domino.side1, domino.side2
            if domino.is_left_orientation:
                self.left_side, self.right_side = domino.side2, domino.side1

    def add_to_right(self, domino):
        # Проверка возможности добавления домино в правую часть цепочки
        # ex_flags = [
        #     domino.is_double and domino.side1 != self.right_side,
        #     domino.is_right_orientation and domino.side1 != self.right_side,
        #     domino.is_left_orientation and domino.side2 != self.right_side
        # ]
        # if any(ex_flags):
        #     raise Exception('Некорректное добавления справа')

        domino_rect = domino.rect
        domino_rect = pg.Rect(
            self.right_line + 2,
            domino_rect.y,
            domino_rect.width,
            domino_rect.height
        )
        self.domino_list.append(ChainElement(domino_rect, domino))
        self.right_line = domino_rect.right

        if domino.is_right_orientation:
            self.right_side = domino.side2
        if domino.is_left_orientation:
            self.right_side = domino.side1

    def add_to_left(self, domino):
        # Проверка возможности добавления домино в левую часть цепочки
        # ex_flags = [
        #     domino.is_double and domino.side1 != self.left_side,
        #     domino.is_right_orientation and domino.side2 != self.left_side,
        #     domino.is_left_orientation and domino.side1 != self.left_side
        # ]
        # if any(ex_flags):
        #     raise Exception('Некорректное добавления слева')

        domino_rect = domino.rect
        domino_rect = pg.Rect(
            self.left_line - 2 - domino_rect.width,
            domino_rect.y,
            domino_rect.width,
            domino_rect.height
        )
        self.domino_list.insert(0, ChainElement(domino_rect, domino))
        self.left_line = domino_rect.left

        if domino.is_right_orientation:
            self.left_side = domino.side1
        if domino.is_left_orientation:
            self.left_side = domino.side2

    def create_surface(self, scope):
        self.surface.fill(self.TRANSPARENT_COLOR)
        scope_domino_list = [(rect, domino) for rect, domino in self.domino_list if scope.rect_in_scope(rect)]
        for rect, domino in scope_domino_list:
            self.surface.blit(domino.surface, (rect.x - scope.left_line, H // 2 - rect.y))

    @property
    def width(self):
        return self.right_line - self.left_line

    @property
    def center_line(self):
        return (self.left_line + self.right_line) // 2
