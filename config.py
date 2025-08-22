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
        name="", # Произвольное название
        image_pos=((0, 0, 0, 0), (0, 0, 0, 0)), # Координаты в формате (Tl X, Tl Y, Px X, Px Y) левого верхнего, правого нижнего угла
        save_file="zone1.png", #  Файл для сохранения изображения зоны
        bot_token="", # Токен бота от @BotFatherr
        chat_id="", # ID чата для уведомлений (можно получить через @getmy_idbot)
        ignored_authors=(), # ID авторов, изменения которых следует игнорировать
        interval=600 # Интервал в секундах (по умолчанию 600)
    ),
]
