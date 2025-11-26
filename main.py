import os
import sqlite3
import random
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
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

# какие команды есть и какому жанру в базе они соответствуют
GENRES = {
    # старые
    "techno": "techno",
    "house": "house",
    "ambient": "ambient",
    "idm": "idm",
    "ebm": "ebm",
    "dark": "dark",

    # новые
    "dubstep": "dubstep",
    "darkjungle": "dark jungle",
    "jungle": "jungle",
    "breakcore": "breakcore",
    "tederfm": "tederfm",
    "afrohouse": "afro house",
    "dubtechno": "dub techno",
    "dub": "dub",
}

# для каждого юзера запоминаем, в какой жанр он сейчас добавляет треки
user_genre = {}  # {user_id: "techno"}


# ===== Команда /add =====
@dp.message_handler(commands=["add"])
async def add_start(msg: types.Message):
    args = msg.get_args()
    if not args:
        await msg.reply("Use: /add techno")
        return

    # что напишешь после /add — так и запишется в жанр
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
@dp.message_handler(commands=list(GENRES.keys()))
async def send_random(msg: types.Message):
    # имя команды без / и параметров
    # пример: "/dubtechno" -> "dubtechno"
    command = msg.text.split()[0][1:].lower()

    genre = GENRES.get(command)
    if not genre:
        await msg.reply("Unknown genre command 🤔")
        return

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
    commands_list = "\n".join(
        f"/{cmd}  →  {genre}" for cmd, genre in GENRES.items()
    )

    await msg.reply(
        "Great. Commands:\n"
        "/add genre  (example: /add techno)\n\n"
        "Play by genre:\n"
        f"{commands_list}"
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
