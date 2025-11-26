import os
import sqlite3
import random
import logging

from aiogram import Bot, Dispatcher, types
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# === Настройки ===
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN env var is not set")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # например: https://tg-mus-bot.onrender.com
if not WEBHOOK_HOST:
    raise RuntimeError("WEBHOOK_HOST env var is not set")

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8000))  # Render передаёт PORT

# === Бот и диспетчер ===
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# === База данных ===
db = sqlite3.connect("music.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre TEXT,
    file_id TEXT
)
""")
db.commit()

# Запоминаем, в какой жанр юзер сейчас добавляет треки
user_genre = {}  # {user_id: "techno"}


# ===== /add =====
@dp.message_handler(commands=["add"])
async def add_start(msg: types.Message):
    args = msg.get_args()
    if not args:
        await msg.reply("Use: /add techno")
        return

    genre = args.strip().lower()
    user_genre[msg.from_user.id] = genre
    await msg.reply(f"Ok. Send me an audio and I'll place it into genre: {genre}")


# ===== Приём аудио после /add =====
@dp.message_handler(content_types=["audio"])
async def add_audio(a_msg: types.Message):
    user_id = a_msg.from_user.id
    genre = user_genre.get(user_id)

    if not genre:
        await a_msg.reply("First choose genre with /add genre (for example /add techno)")
        return

    file_id = a_msg.audio.file_id
    cursor.execute(
        "INSERT INTO albums (genre, file_id) VALUES (?, ?)",
        (genre, file_id),
    )
    db.commit()
    await a_msg.reply(f"Added to {genre} 🔥")


# ===== Выбор случайного трека по жанру =====
@dp.message_handler(commands=[
    "techno", "house", "ambient", "idm", "ebm", "dark",
    "dubstep", "darkjungle", "jungle", "breakcore",
    "tederfm", "afrohouse", "dubtechno", "dub"
])
async def send_random(msg: types.Message):
    genre = msg.text.replace("/", "").lower()
    cursor.execute("SELECT file_id FROM albums WHERE genre=?", (genre,))
    rows = cursor.fetchall()

    if not rows:
        await msg.reply(f"No albums in genre {genre}")
        return

    file_id = random.choice(rows)[0]
    await msg.answer_audio(file_id)


# ===== /start =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.reply(
        "Great. Commands:\n"
        "/add genre\n"
        "/techno\n"
        "/house\n"
        "/ambient\n"
        "/idm\n"
        "/ebm\n"
        "/dark\n"
        "/dubstep\n"
        "/darkjungle\n"
        "/jungle\n"
        "/breakcore\n"
        "/tederfm\n"
        "/afrohouse\n"
        "/dubtechno\n"
        "/dub"
    )


# ===== Webhook-хендлер для Telegram =====
async def handle_webhook(request: web.Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()


# ===== Хуки старта/остановки aiohttp-приложения =====
async def on_startup(app: web.Application):
    # Сначала удаляем старый webhook (если был), потом ставим новый
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set to {WEBHOOK_URL}")


async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    db.close()
    await bot.session.close()
    logging.info("Bot shutdown completed")


def main():
    app = web.Application()
    # Роут, куда Telegram будет слать апдейты
    app.router.add_post(WEBHOOK_PATH, handle_webhook)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == "__main__":
    main()

