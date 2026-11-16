#!/usr/bin/env python3
"""Точка входа: ``python3 start.py`` или ``python3 -m domino``."""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap() -> None:
    """Запуск из любой папки: путь к игре и рабочий каталог внутри неё."""
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import os

    os.chdir(root)


def main() -> int:
    _bootstrap()
    from domino.ui.app import main as app_main

    return app_main(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
