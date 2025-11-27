import os
import sqlite3
import random
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, types

logging.basicConfig(level=logging.INFO)

# === НАСТРОЙКИ ===
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("Environment variable TOKEN is not set")

# адрес твоего сервиса на Render
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://tg-mus-bot-gfix.onrender.com")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", "8000"))  # Render сам подставит PORT


# === БОТ И ДИСПЕТЧЕР ===
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ВАЖНО: фикс для aiogram в webhook-режиме
Bot.set_current(bot)
Dispatcher.set_current(dp)


# === БАЗА ДАННЫХ ===
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

# запоминаем, в какой жанр пользователь сейчас кидает треки
user_genre = {}  # {user_id: "techno"}


# === ЖАНРЫ И КОМАНДЫ ===
GENRE_COMMANDS = {
    "techno": "techno",
    "house": "house",
    "ambient": "ambient",
    "idm": "idm",
    "ebm": "ebm",
    "dark": "dark",
    "dubstep": "dubstep",
    "darkjungle": "dark jungle",
    "jungle": "jungle",
    "breakcore": "breakcore",
    "tederfm": "tederfm",
    "afrohouse": "afro house",
    "dubtechno": "dub techno",
    "dub": "dub",
}


# ====== /add ======
@dp.message_handler(commands=["add"])
async def add_start(msg: types.Message):
    args = msg.get_args()
    if not args:
        await msg.reply("Use: /add genre\nНапример: /add techno")
        return

    genre = args.strip().lower()
    user_genre[msg.from_user.id] = genre
    await msg.reply(f"Ок. Жду аудио, сохраню в жанр: {genre}")


# ====== Приём аудио после /add ======
@dp.message_handler(content_types=["audio"])
async def add_audio(a_msg: types.Message):
    user_id = a_msg.from_user.id
    genre = user_genre.get(user_id)

    if not genre:
        await a_msg.reply("Сначала выбери жанр командой /add genre\nНапример: /add techno")
        return

    file_id = a_msg.audio.file_id
    cursor.execute(
        "INSERT INTO albums (genre, file_id) VALUES (?, ?)",
        (genre, file_id),
    )
    db.commit()
    await a_msg.reply(f"Добавил в {genre} 🔥")


# ====== Выбор случайного трека по жанру ======
@dp.message_handler(commands=list(GENRE_COMMANDS.keys()))
async def send_random(msg: types.Message):
    cmd = msg.text.split()[0].lstrip("/").lower()
    genre = GENRE_COMMANDS.get(cmd, cmd)

    cursor.execute("SELECT file_id FROM albums WHERE genre = ?", (genre,))
    rows = cursor.fetchall()

    if not rows:
        await msg.reply(f"В жанре {genre} ещё ничего нет")
        return

    file_id = random.choice(rows)[0]
    await msg.answer_audio(file_id)


# ====== /start ======
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    commands_text = "\n".join(
        f"/{cmd}" for cmd in GENRE_COMMANDS.keys()
    )
    await msg.reply(
        "Yo. Команды:\n"
        "/add genre  — добавить трек в жанр (пример: /add techno)\n\n"
        "Жанры:\n"
        f"{commands_text}"
    )


# ========= AIOHTTP (WEBHOOK) =========

async def handle_root(request: web.Request):
    # просто 404, чтобы Render был доволен
    return web.Response(text="Not found", status=404)


async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(text="bad request", status=400)

    update = types.Update(**data)
    logging.info("Got update: %s", update)

    await dp.process_update(update)
    return web.Response(text="ok", status=200)


async def on_startup(app: web.Application):
    # снимаем старый вебхук на всякий случай
    await bot.delete_webhook()
    # ставим новый
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook set to %s", WEBHOOK_URL)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
