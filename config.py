from dataclasses import dataclass
from typing import Tuple

@dataclass
class ZoneConfig:
    name: str
    image_pos: Tuple[Tuple[int, int, int, int], ...]
    save_file: str
    bot_token: str
    chat_id: str
    interval: int = 600
    ignored_authors: Tuple[int, ...] = ()


zones = [
    ZoneConfig(
        name="Арт 1",  # Название зоны (любое для удобства)
        image_pos=((0, 0, 100, 100), (100, 100, 200, 200)),  # Координаты: (Tile X, Tile Y, Pixel X, Pixel Y)
        save_file="zone1.png",  # Файл для сохранения текущего состояния зоны
        bot_token="...",  # Токен Telegram-бота (получить у @BotFather)
        chat_id="...",  # ID чата или канала для уведомлений
        ignored_authors=(),  # Игнорируемые авторы (их ID можно узнать через API)
        interval=600,  # Интервал проверки в секундах (по умолчанию 600 = 10 минут)
        use_white_bg=True # Отправлять видео с белым фоном вместо чёрного
    ),
]
