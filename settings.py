# Ширина и высота окна
W, H = 1600, 850

# Заголовок окна
WINDOW_TITLE = 'Domino'

# Частота кадров
FPS = 30

# Цвета для фона
BACKGROUND_COLORS = [
    (50, 120, 220),
    (10, 100, 200)
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

# Цвета для обратной стороны домино
DOMINO_BACKSIDE_COLOR_1 = (224, 207, 177)
DOMINO_BACKSIDE_COLOR_2 = (255, 229, 180)

# Положение панели с крайним левым домино в цепочке
LEFT_EDGE_PANE_COORDS = (CELL_SIZE // 2, H // 2 - int(3.5 * CELL_SIZE))

# Положение панели с крайним правым домино в цепочке
RIGHT_EDGE_PANE_COORDS = (W - (2 * CELL_SIZE + CELL_SIZE // 2), H // 2 - int(3.5 * CELL_SIZE))

# Полжение панели с "хранилищем"
STORAGE_PANE_COORDS = (W - 3 * CELL_SIZE, CELL_SIZE // 2)

# Интервал между домино в пулах
POOL_DOMINO_INTERVAL = CELL_SIZE + 5

# Режимы игры
PLAYER_MOVE_MODE = 1    # Ход игрока
CMP_MOVE_MODE = 2       # Ход компьютера
END_GAME_MODE = 3       # Игра окончена, вывод результатов
