import threading
from main import run_bot
from config import zones

threads = []

for zone in zones:
    t = threading.Thread(
        target=run_bot,
        args=(
            zone.name,
            zone.image_pos,
            zone.save_file,
            zone.bot_token,
            zone.chat_id,
            zone.interval,
            zone.ignored_authors
        ),
        daemon=True
    )
    t.start()
    threads.append(t)

for t in threads:
    t.join()
