import asyncio

from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot import bot, dp
from app.database.db import conn
from app.database.init_db import init_database
from app.database.init_db import seed_database
from app.database.init_db import is_db_empty
from app.announcement_scheduler import scheduler
from app.handlers.help_handlers import setup_commands

import app.handlers.game_handlers
import app.handlers.player_handlers
import app.handlers.historic_match_handlers
import app.handlers.stats_handlers
import app.handlers.help_handlers
import app.handlers.setup


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("⚽ Football bot is running!")


async def main():  
    init_database()
    if is_db_empty():
        seed_database()
    await setup_commands()
    scheduler.start() # Запускаем планировщик новостей
    print("Bot started")

    try:
        await dp.start_polling(bot)
    finally:
        conn.close()
        print("Database closed")


if __name__ == "__main__":
    asyncio.run(main())