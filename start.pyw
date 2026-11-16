"""Запуск Домино без консольного окна (Windows: двойной клик по файлу)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap() -> None:
    """Гарантирует импорт пакета ``domino`` при запуске из любой папки.

    Нужно для Windows: двойной клик по ``start.pyw`` запускает файл с рабочим
    каталогом, отличным от папки игры, поэтому путь добавляем явно.
    """
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # Кириллица в пути к папке игры не должна ломать запуск на Windows.
    os.chdir(root)


def main() -> int:
    _bootstrap()
    from domino.ui.app import main as app_main

    return app_main(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
