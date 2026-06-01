import asyncio


import app.handlers.game_handlers
import app.handlers.player_handlers
import app.handlers.historic_match_handlers
import app.handlers.stats_handlers
import app.handlers.help_handlers

from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot import bot, dp 
from app.database.db import conn

from app.database.init_db import init_database


# /START command
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("⚽ Football bot is running!")

async def main():
    init_database()
    try:
        print("Bot started")
        await dp.start_polling(bot)
    finally:
        conn.close()
        print("Database closed")

if __name__ == "__main__":
    asyncio.run(main())