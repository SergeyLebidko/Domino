"""Пользовательские настройки: тема, сложность, первый ход.

Файл лежит рядом с игрой (``settings.json`` в корне проекта) — игра не пишет
ничего за пределы своей папки. Чтение и запись молчаливые: если файла нет или
записать не удалось (нет прав, папка только для чтения), игра просто работает
с настройками по умолчанию.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from domino import settings

#: Корень игры — папка, в которой лежит пакет ``domino``.
GAME_DIR = Path(__file__).resolve().parent.parent

#: Файл настроек внутри папки игры.
CONFIG_NAME = 'settings.json'

CONFIG_PATH = GAME_DIR / CONFIG_NAME


@dataclass
class Config:
    theme: str = settings.DEFAULT_THEME
    difficulty: str = settings.DEFAULT_DIFFICULTY
    first_player: int = 0

    @classmethod
    def load(cls, path: Path | None = None) -> 'Config':
        path = path or CONFIG_PATH
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()

        config = cls()
        if data.get('theme') in settings.THEME_KEYS:
            config.theme = data['theme']
        if data.get('difficulty') in settings.DIFFICULTY_KEYS:
            config.difficulty = data['difficulty']
        if data.get('first_player') in (0, 1):
            config.first_player = int(data['first_player'])
        return config

    def save(self, path: Path | None = None) -> bool:
        """Сохраняет настройки рядом с игрой. Возвращает успех записи."""
        path = path or CONFIG_PATH
        temporary = path.with_name(path.name + '.tmp')
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            os.replace(temporary, path)
            return True
        except OSError:
            try:
                temporary.unlink()
            except OSError:
                pass
            return False
