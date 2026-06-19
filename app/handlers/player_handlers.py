from aiogram.filters import Command
from aiogram.types import Message
from app.database.db import conn, cursor
from aiogram.exceptions import TelegramBadRequest  

from app.bot import dp, bot
from app.state.game_state import *
from app.utils.helpers import (
    is_admin,
    get_player_id,
    get_active_match_id,
    get_player_rating,
    safe_delete,
    get_game_status,
    format_lineup
)
from app.data import players, player_ratings, telegram_usernames
from app.config import ADMINS


@dp.message(Command("register"))
async def register_handler(message: Message):

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/register Фамилия"
        )
        return

    player_name = parts[1].strip().title()
    telegram_id = message.from_user.id

    # =========================
    # Проверяем, не зарегистрирован ли уже этот Telegram
    # =========================

    cursor.execute("""
        SELECT name
        FROM players
        WHERE telegram_id = ?
    """, (telegram_id,))

    existing_player = cursor.fetchone()

    if existing_player:
        await message.answer(
            f"Вы уже зарегистрированы как "
            f"{existing_player[0]}"
        )
        return

    # =========================
    # Ищем игрока
    # =========================

    cursor.execute("""
        SELECT id, telegram_id
        FROM players
        WHERE name = ?
    """, (player_name,))

    player = cursor.fetchone()

    if not player:
        await message.answer(
            "Игрок не найден.\n"
            "Обратитесь к администратору."
        )
        return

    player_id, existing_telegram_id = player

    # =========================
    # Игрок уже привязан
    # =========================

    if existing_telegram_id is not None:
        await message.answer(
            f"{player_name} уже зарегистрирован."
        )
        return

    # =========================
    # Привязка Telegram
    # =========================

    cursor.execute("""
        UPDATE players
        SET telegram_id = ?
        WHERE id = ?
    """, (
        telegram_id,
        player_id
    ))

    conn.commit()

    await message.answer(
        f"✅ {player_name} успешно зарегистрирован."
    )

#  RATINGS command to see list of ratings
@dp.message(Command("ratings"))
async def ratings_handler(message: Message):
    await safe_delete(message)
    cursor.execute("""
    SELECT name, rating
    FROM players
    ORDER BY rating DESC
    """)

    players = cursor.fetchall()

    text = "🏆 Рейтинги игроков:\n\n"

    for i, (name, rating) in enumerate(players, start=1):
        text += f"{i}. {name} — {rating}\n"

    await bot.send_message(message.from_user.id, text)

# /PLAYERS command
@dp.message(Command("players"))
async def players_handler(message: Message):
    await safe_delete(message)
    text = "Игроки:\n\n"
    shirt = 0
    for player in players:
        shirt += 1
        text += f"{shirt}. {player}\n"
    
    await bot.send_message(message.from_user.id, text)

# SET RATING command
@dp.message(Command("setrating"))
async def setrating_handler(message: Message):
    await safe_delete(message)
    if not is_admin(message.from_user.id):
        return
    
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    parts = message.text.split()

    if len(parts) != 3:
        await bot.send_message (message.from_user.id, 
            "Использование:\n/setrating Murzinov 8")
        return

    player_name = parts[1].title().strip()

    try:
        new_rating = int(parts[2])
    except ValueError:
        await bot.send_message(message.from_user.id, "Рейтинг должен быть числом.")
        return

    cursor.execute("""
    UPDATE players
    SET rating = ?
    WHERE name = ?
    """, (new_rating, player_name))

    conn.commit()

    if cursor.rowcount == 0:
        await bot.send_message(message.from_user.id, "Игрок не найден.")
        return

    await bot.send_message(message.from_user.id,
        f"Рейтинг {player_name} изменен на {new_rating}"
    )

#  /NEWPLAYER command
@dp.message(Command("newplayer"))
async def newplayer_handler(message: Message):

    await safe_delete(message)
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()

    if len(parts) < 2:
        await bot.send_message(message.from_user.id,
            "Использование:\n/newplayer Фамилия"
        )
        return

    player_name = parts[1].title().strip()

    # проверяем существует ли уже игрок
    cursor.execute("""
    SELECT *
    FROM players
    WHERE name = ?
    """, (player_name,))

    existing_player = cursor.fetchone()

    if existing_player:
        await bot.send_message(message.from_user.id,
            f"{player_name} уже существует."
        )
        return

    # создаем игрока
    cursor.execute("""
    INSERT INTO players (name, rating)
    VALUES (?, ?)
    """, (player_name, 0))

    conn.commit()

    # добавляем в список players в памяти
    players.append(player_name)

    await bot.send_message(message.from_user.id, 
        f"✅ Игрок {player_name} создан."
    )
