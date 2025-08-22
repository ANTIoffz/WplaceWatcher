import os
import time
from io import BytesIO
from functools import lru_cache
from typing import List, Tuple, Union
import imageio
import cv2
import numpy as np

import requests
from PIL import Image, ImageChops
import logging



# -----------------------------
# Конфиг
# -----------------------------

TILE_SIZE = 1000
URL_TEMPLATE = "https://backend.wplace.live/files/s0/tiles/{tlx}/{tly}.png"
URL_AUTHOR_TEMPLATE = "https://backend.wplace.live/s0/pixel/{tlx}/{tly}?x={x}&y={y}"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SEND_VIDEO_INSTEAD_OF_GIF = True # Отправлять MP4 вместо GIF, для телеграма лучше, так как гифки сильно сжимаются 
TEST_DONT_SAVE_ZONE = False # Не сохранять изменения (для отладки)
SEND_FILTERED = False # Отправлять сообщение об изменениях даже от игнорируемых авторов, добавляется только восклицательный знак в начале сообщения, если изменения не от пользователя из фильтра 

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# -----------------------------

def send_telegram_message(
    text: str,
    token: str,
    chat_id: str,
    gif: BytesIO = None,
    video: BytesIO = None
) -> dict:
    try:
        if gif:
            url = f"https://api.telegram.org/bot{token}/sendAnimation"
            files = {"animation": ("diff.gif", gif, "image/gif")}
            data = {"chat_id": chat_id, "caption": text, "parse_mode": "Markdown"}
        elif video:
            url = f"https://api.telegram.org/bot{token}/sendVideo"
            files = {"video": ("diff.mp4", video, "video/mp4")}
            data = {"chat_id": chat_id, "caption": text, "parse_mode": "Markdown"}
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            files = None
            data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

        resp = requests.post(url, data=data, files=files)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        return {}


def send_request(url: str, data: dict, retries: int = 5, delay: int = 2, dead_delay: int = 60) -> requests.Response:
    url = url.format(**data)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code in (429, 503, 521):
                raise requests.HTTPError(f"{resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except Exception as e:
            code = getattr(e.response, "status_code", None)
            if attempt < retries:
                sleep_time = dead_delay if code == 521 else delay
                logging.error(f"Ошибка {e}, повтор через {sleep_time} сек (попытка {attempt}/{retries})")
                time.sleep(sleep_time)
            else:
                raise


def fetch_tile(tlx: int, tly: int) -> Image.Image:
    resp = send_request(URL_TEMPLATE, {"tlx": tlx, "tly": tly})
    return Image.open(BytesIO(resp.content))


def fetch_pixel(tlx: int, tly: int, x: int, y: int) -> dict:
    resp = send_request(URL_AUTHOR_TEMPLATE, {"tlx": tlx, "tly": tly, "x": x, "y": y})
    return resp.json()


def upscale_min(img: Image.Image, min_size: int = 320) -> Image.Image:
    w, h = img.size
    scale = max(1, -(-min_size // w), -(-min_size // h))
    new_size = (w * scale, h * scale)
    return img.resize(new_size, Image.NEAREST)


def make_diff_gif(img_old: Image.Image, img_new: Image.Image) -> BytesIO:
    img_old = upscale_min(img_old)
    img_new = upscale_min(img_new)
    bio = BytesIO()
    img_old.save(
        bio,
        format="GIF",
        save_all=True,
        append_images=[img_new],
        duration=1000,
        loop=0
    )
    bio.seek(0)
    return bio



def make_diff_video(img_old: Image.Image, img_new: Image.Image, fps: int = 1) -> BytesIO:
    img_old = upscale_min(img_old)
    img_new = upscale_min(img_new)

    w, h = img_old.size
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    bio_path = '/tmp/temp_video.mp4'

    out = cv2.VideoWriter(bio_path, fourcc, fps, (w, h))

    for frame in [img_old, img_new]:
        frame_bgr = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)

    out.release()

    bio = BytesIO()
    with open(bio_path, 'rb') as f:
        bio.write(f.read())
    bio.seek(0)
    os.remove(bio_path)
    return bio


def get_area(image_pos: Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]) -> Image.Image:
    (tx1, ty1, x1, y1), (tx2, ty2, x2, y2) = image_pos

    min_tx, max_tx = min(tx1, tx2), max(tx1, tx2)
    min_ty, max_ty = min(ty1, ty2), max(ty1, ty2)

    big_width = (max_tx - min_tx + 1) * TILE_SIZE
    big_height = (max_ty - min_ty + 1) * TILE_SIZE
    big_img = Image.new("RGB", (big_width, big_height))

    for tx in range(min_tx, max_tx + 1):
        for ty in range(min_ty, max_ty + 1):
            tile = fetch_tile(tx, ty)
            ox = (tx - min_tx) * TILE_SIZE
            oy = (ty - min_ty) * TILE_SIZE
            big_img.paste(tile, (ox, oy))

    gx1 = (tx1 - min_tx) * TILE_SIZE + x1
    gy1 = (ty1 - min_ty) * TILE_SIZE + y1
    gx2 = (tx2 - min_tx) * TILE_SIZE + x2
    gy2 = (ty2 - min_ty) * TILE_SIZE + y2

    return big_img.crop((gx1, gy1, gx2, gy2))


def get_changed_pixels(img1: Image.Image, img2: Image.Image, image_pos: Tuple[Tuple[int, int, int, int], ...]) -> Union[str, List[Tuple[int, int, int, int]]]:
    if img1.size != img2.size:
        return "size"

    min_tx = min(image_pos[0][0], image_pos[1][0])
    min_ty = min(image_pos[0][1], image_pos[1][1])
    x_offset = image_pos[0][2]
    y_offset = image_pos[0][3]

    w, h = img1.size
    pix1, pix2 = img1.load(), img2.load()
    changed = []

    for y in range(h):
        for x in range(w):
            if pix1[x, y] != pix2[x, y]:
                global_x = (min_tx * TILE_SIZE) + x_offset + x
                global_y = (min_ty * TILE_SIZE) + y_offset + y

                tile_x, tile_y = divmod(global_x, TILE_SIZE)[0], divmod(global_y, TILE_SIZE)[0]
                local_x, local_y = global_x % TILE_SIZE, global_y % TILE_SIZE

                changed.append((tile_x, tile_y, local_x, local_y))

    return changed


def images_diff(img1: Image.Image, img2: Image.Image) -> bool:
    """Проверка, есть ли различия между изображениями."""
    if img1.size != img2.size:
        return True
    diff = ImageChops.difference(img1, img2)
    return bool(diff.getbbox())


def main(
    zone_name: str,
    image_pos: Tuple[Tuple[int, int, int, int], ...],
    save_file: str,
    bot_token: str,
    chat_id: str,
    interval: int = 600,
    ignored_authors: Tuple[int, ...] = ()
):
    new_data = get_area(image_pos)

    if os.path.exists(save_file):
        old_data = Image.open(save_file)
        changed_pixels = get_changed_pixels(old_data, new_data, image_pos)

        if not changed_pixels:
            logging.info(f"[{zone_name}] Изменений нет")
        elif changed_pixels == "size":
            logging.info(f"[{zone_name}] Размер зоны изменён, обновление")
            new_data.save(save_file)
        else:
            if not TEST_DONT_SAVE_ZONE:
                new_data.save(save_file)
            logging.info(f"[{zone_name}] ⚠️ Обнаружены изменения в {len(changed_pixels)} пикселях")
            pixel_data = fetch_pixel(*changed_pixels[0])
            pixel_author = pixel_data.get('paintedBy', {})
            logging.info(f"[{zone_name}] ⚠️ Автор {changed_pixels[0]}: {pixel_author}")


            if int(pixel_author.get('id', 0)) not in ignored_authors or SEND_FILTERED:
                text = f"""
{"" if int(pixel_author.get('id', 0)) in ignored_authors else "⚠️"} *{zone_name}* - *Изменения в {len(changed_pixels)} пикселях* 

👤 *Автор первого пикселя:*
- Ник: `{pixel_author.get('name')} #{pixel_author.get('id')}`
- Дискорд: `@{pixel_author.get('discord', "Отсутствует")}`
- Клан: `{pixel_author.get('allianceName', "Отсутствует")}`

📍 *Координаты первых 10 изменённых пикселей:*  
{"\n".join(f"• {px[0]}, {px[1]}, {px[2]}, {px[3]}" for px in changed_pixels[:10])}
"""
                if not SEND_VIDEO_INSTEAD_OF_GIF:
                    send_telegram_message(
                        text,
                        token=bot_token,
                        chat_id=chat_id,
                        gif=make_diff_gif(old_data, new_data)
                    )
                else:
                    send_telegram_message(
                        text,
                        token=bot_token,
                        chat_id=chat_id,
                        video=make_diff_video(old_data, new_data)
                    )
            else:
                logging.info(f"[{zone_name}] Автор в белом списке")
    else:
        logging.info(f"[{zone_name}] Сохраняю первый файл")
        new_data.save(save_file)

    time.sleep(interval)


def run_bot(
    zone_name: str,
    image_pos: Tuple[Tuple[int, int, int, int], ...],
    save_file: str,
    bot_token: str,
    chat_id: str,
    interval: int = 600,
    ignored_authors: Tuple[int, ...] = ()
):
    while True:
        try:
            main(zone_name, image_pos, save_file, bot_token, chat_id, interval, ignored_authors)
        except Exception as e:
            logging.error(f"[{zone_name}] ОШИБКА: {e}")
            time.sleep(interval)
