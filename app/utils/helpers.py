from app.config import ADMINS
from app.database.db import cursor
from aiogram.exceptions import TelegramBadRequest
from app.state.game_state import game_state, MIN_PLAYERS, MAX_PLAYERS
from aiogram.types import Message


# helper to check if Admin
def is_admin(user_id):
    return user_id in ADMINS


# helper function for database to get player id by name
def get_player_id(name):

    cursor.execute("""
    SELECT id
    FROM players
    WHERE name = ?
    """, (name,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


# helper function for database to get active match id
def get_active_match_id():

    cursor.execute("""
    SELECT id
    FROM matches
    WHERE is_active = 1
    ORDER BY id DESC
    LIMIT 1
    """)

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


# helper to get ratings from DB
def get_player_rating(name):

    cursor.execute("""
    SELECT rating
    FROM players
    WHERE name = ?
    """, (name,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0


# helper function for delete messages in tg
async def safe_delete(message: Message):

    try:
        await message.delete()

    except TelegramBadRequest:
        pass


# helper the game status
def get_game_status():

    players_count = len(game_state.players_for_game)

    if not game_state.game_active:
        return "Нет активной игры."

    elif players_count < MIN_PLAYERS:

        return (
            f"Игроков {players_count}\n"
            f"До игры нужно еще "
            f"{MIN_PLAYERS - players_count} игроков."
        )

    elif players_count == MIN_PLAYERS:

        return (
            f"Игроков {players_count}/{MAX_PLAYERS}\n"
            f"Можно бронировать поле\n"
            f"Продолжаем набор до {MAX_PLAYERS}"
        )

    elif players_count < MAX_PLAYERS:

        return (
            f"Игроков {players_count}/{MAX_PLAYERS}\n"
            f"Продолжаем набор до {MAX_PLAYERS}"
        )

    else:

        return (
            f"Игроков {players_count}/{MAX_PLAYERS}\n"
            f"Набор окончен, можно играть!"
        )


# helper lineup formatting
def format_lineup(player_list):

    if not player_list:
        return "Список игроков пуст."

    return (
        "Состав игроков:\n\n"
        + "\n".join(f"• {player}" for player in player_list)
    )