import sqlite3
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# create base
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

# Command /add genre
@dp.message_handler(commands=["add"])
async def add_start(msg: types.Message):
    args = msg.get_args()
    if not args:
        return await msg.reply("Use: /add techno")

    genre = args.strip().lower()
    await msg.reply(f"Ok. Send me an audio and i'll place it into genre: {genre}")

    @dp.message_handler(content_types=["audio"])
    async def add_audio(a_msg: types.Message):
        file_id = a_msg.audio.file_id
        cursor.execute("INSERT INTO albums (genre, file_id) VALUES (?, ?)", (genre, file_id))
        db.commit()
        await a_msg.reply("Added 🔥")

# example: /techno
@dp.message_handler(commands=["techno", "house", "ambient", "idm", "ebm", "dark"])
async def send_random(msg: types.Message):
    genre = msg.text.replace("/", "").lower()
    cursor.execute("SELECT file_id FROM albums WHERE genre=?", (genre,))
    rows = cursor.fetchall()

    if not rows:
        return await msg.reply(f"No albums in genre {genre}")

    file_id = random.choice(rows)[0]
    await msg.answer_audio(file_id)

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.reply("Great. Commands:\n/add genre\n/techno\n/house\n/ambient\n/idm\n/ebm\n/dark")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
