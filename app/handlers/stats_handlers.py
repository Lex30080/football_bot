from aiogram.filters import Command
from aiogram.types import Message

from app.bot import dp
from app.database.db import cursor


@dp.message(Command("topscorers"))
async def topscorers_handler(message: Message):

    cursor.execute("""
    SELECT
        players.name,
        COUNT(goals.id) as goals_count
    FROM goals

    JOIN players
        ON goals.scorer_id = players.id

    GROUP BY players.id

    ORDER BY goals_count DESC

    LIMIT 10
    """)

    scorers = cursor.fetchall()

    if not scorers:
        await message.answer("⚽ Пока нет голов.")
        return

    text = "🏆 Топ бомбардиров:\n\n"

    for index, (name, goals) in enumerate(scorers, start=1):

        text += f"{index}. {name} — {goals}\n"

    await message.answer(text)