import pygame as pg
from settings import CELL_SIZE, DOMINO_BACKGROUND_COLOR, DOMINO_BORDER_COLOR, DOMINO_DOT_COLOR


class Domino:
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

        dot_list = self.dot_data[self.side1]
        for dot in dot_list:
            dot_coords.append((left_x0 + dot[0] * dx, left_y0 + dot[1] * dy))

        dot_list = self.dot_data[self.side2]
        for dot in dot_list:
            dot_coords.append((right_x0 + dot[0] * dx, right_y0 + dot[1] * dy))

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

    def rotate(self):
        pass
