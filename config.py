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
        name="", # Название арта
        image_pos=((0, 0, 0, 0), (0, 0, 0, 0)), # Координаты в формате (Tl X, Tl Y, Px X, Px Y) левый верхний - правый нижний угол
        save_file="zone1.png", # Название файла для сохранения изображения
        bot_token="", # Токен телеграмм бота с @BotFather
        chat_id="", # Айди телеграмм чата для отправки сообщений @getmy_idbot
        ignored_authors=() # Айди авторов для игнорирования
    ),
]
