# Ширина и высота окна
W, H = 1600, 850

# Заголовок окна
WINDOW_TITLE = 'Domino'

# Частота кадров
FPS = 30

# Цвета для фона
BACKGROUND_COLORS = [
    (120, 120, 120),
    (110, 110, 110)
]

# Размер одного мономино в составе домино
CELL_SIZE = 60

# Цвет домино
DOMINO_BACKGROUND_COLOR = (240, 240, 240)

# Цвет границ домино
DOMINO_BORDER_COLOR = (0, 0, 0)

# Цвет точек на домино
DOMINO_DOT_COLOR = (0, 0, 0)

# Цвет для "прозрачных" заливок
TRANSPARENT_COLOR = (255, 0, 0)

# Положение панели с крайним левым домино в цепочке
LEFT_EDGE_PANE_COORDS = (CELL_SIZE // 2, H // 2 - int(3.5 * CELL_SIZE))

# Положение панели с крайним правым домино в цепочке
RIGHT_EDGE_PANE_COORDS = (W - (2 * CELL_SIZE + CELL_SIZE // 2), H // 2 - int(3.5 * CELL_SIZE))

# Полжение панели с "хранилищем"
STORAGE_PANE_COORDS = (W - 3 * CELL_SIZE, CELL_SIZE // 2)
