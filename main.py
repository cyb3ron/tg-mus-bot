import os
import sqlite3
import random
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook

logging.basicConfig(level=logging.INFO)

# === TOKEN ===
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("No TOKEN env var set")

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

# для каждого юзера запоминаем, в какой жанр он сейчас добавляет треки
user_genre = {}  # {user_id: "techno"}

# ===== Команда /add =====
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

# Список жанров, которые бот умеет
GENRES = [
    "techno",
    "house",
    "ambient",
    "idm",
    "ebm",
    "dark",
    "dubstep",
    "darkjungle",
    "jungle",
    "breakcore",
    "tederfm",
    "afrohouse",
    "dubtechno",
    "dub",
]

# ===== Выбор случайного трека по жанру =====
@dp.message_handler(commands=GENRES)
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
    cmds = "\n".join(f"/{g}" for g in GENRES)
    await msg.reply(
        "Great. Commands:\n"
        "/add genre\n"
        f"{cmds}"
    )

# ========== WEBHOOK CONFIG ==========
WEBHOOK_HOST = "https://tg-mus-bot-gfix.onrender.com"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

WEBAPP_HOST = "0.0.0.0"
port_env = os.getenv("PORT")
try:
    WEBAPP_PORT = int(port_env) if port_env not in (None, "") else 8000
except ValueError:
    WEBAPP_PORT = 8000

async def on_startup(dp: Dispatcher):
    # Удаляем старый webhook (если был) и ставим новый
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(dp: Dispatcher):
    logging.info("Shutting down..")
    await bot.delete_webhook()
    db.close()
    await bot.session.close()
    logging.info("Bye!")

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
