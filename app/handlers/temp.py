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

print("HISTORIC HANDLERS LOADED")

# implementaion of the /oldmatch command
@dp.message(Command("oldmatch"))
async def newmatch_handler(message: Message):
    if not is_admin(message.from_user.id):
        return

    await safe_delete(message)
    # деактивируем прошлые матчи
    cursor.execute("""
    UPDATE matches
    SET is_active = 0
    WHERE is_active = 1
    """)

    # создаем новый матч
    cursor.execute("""
    INSERT INTO matches (
        match_date,
        is_active,
        status
    )
    VALUES (
        DATETIME('now'),
        1,
        'active'
    )
    """)

    conn.commit()

    match_id = cursor.lastrowid

    await bot.send_message(message.from_user.id, 
        f"Создан матч #{match_id}, заполни информацию о матче"
    )

#  /ADD command for old matches
@dp.message(Command("add"))
async def add_player_handler(message: Message):
    await safe_delete(message)
    if not is_admin(message.from_user.id):
        return

    match_id = get_active_match_id()

    if match_id is None:
        await bot.send_message(message.from_user.id,
            "Нет активного матча.\nСначала создайте матч."
        )
        return

    parts = message.text.split()

    if len(parts) < 3:
        await bot.send_message(message.from_user.id,
            "Использование:\n/add red Murzinov"
        )
        return

    team = parts[1].lower()

    if team not in ["red", "green"]:
        await bot.send_message(message.from_user.id,
            "Команда должна быть red или green"
        )
        return

    players_to_add = [
    player.strip().title()
    for player in parts[2:]
]

    added_players = []

    for player_name in players_to_add:

        # добавляем игрока в players если его нет
        cursor.execute("""
        INSERT OR IGNORE INTO players (name)
        VALUES (?)
        """, (player_name,))

        conn.commit()

        player_id = get_player_id(player_name)

        # проверяем уже добавлен или нет
        cursor.execute("""
        SELECT *
        FROM match_players
        WHERE match_id = ?
        AND player_id = ?
        """, (match_id, player_id))

        exists = cursor.fetchone()

        if exists:
            continue

        cursor.execute("""
        INSERT INTO match_players (
            match_id,
            player_id,
            team
        )
        VALUES (?, ?, ?)
        """, (match_id, player_id, team))

        added_players.append(player_name)

    conn.commit()

    if added_players:
        await bot.send_message(message.from_user.id,
            f"Добавлены в {team}:\n" +
            "\n".join(added_players)
        )
    else:
        await bot.send_message(message.from_user.id, "Никто не был добавлен.")


#  /MATCHES command
@dp.message(Command("matches"))
async def matches_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    await safe_delete(message)

    parts = message.text.split()

    # по умолчанию показываем 5
    limit = 5
    show_all = False

    # если есть аргумент
    if len(parts) > 1:

        arg = parts[1].lower()

        if arg == "all":
            show_all = True

        else:
            try:
                limit = int(arg)
            except ValueError:
                await bot.send_message(message.from_user.id,
                    "Использование:\n"
                    "/matches\n"
                    "/matches 20\n"
                    "/matches all"
                )
                return

    # запрос в БД
    if show_all:

        cursor.execute("""
        SELECT id,
               match_date,
               red_score,
               green_score,
               status
        FROM matches
        ORDER BY id DESC
        """)

    else:

        cursor.execute("""
        SELECT id,
               match_date,
               red_score,
               green_score,
               status
        FROM matches
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

    matches = cursor.fetchall()

    if not matches:
        await bot.send_message(message.from_user.id,
            "Матчей пока нет."
        )
        return

    text = "📋 Матчи:\n\n"

    for match in matches:

        match_id = match[0]
        match_date = match[1]
        red_score = match[2]
        green_score = match[3]
        status = match[4]

        text += (
            f"#{match_id} | "
            f"{red_score}:{green_score} | "
            f"{status}\n"
        )

    await bot.send_message(message.from_user.id,text)

# /DELETEMATCH command
@dp.message(Command("deletematch"))
async def deletematch_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:
        await bot.send_message(
            message.from_user.id,
            "Использование:\n/deletematch 15"
        )
        await safe_delete(message)
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await bot.send_message(
            message.from_user.id,
            "ID матча должен быть числом."
        )
        await safe_delete(message)
        return

    # проверяем существует ли матч
    cursor.execute("""
    SELECT id
    FROM matches
    WHERE id = ?
    """, (match_id,))

    match = cursor.fetchone()

    if not match:
        await bot.send_message(
            message.from_user.id,
            "Матч не найден."
        )
        await safe_delete(message)
        return

    # удаляем голы
    cursor.execute("""
    DELETE FROM goals
    WHERE match_id = ?
    """, (match_id,))

    # удаляем игроков матча
    cursor.execute("""
    DELETE FROM match_players
    WHERE match_id = ?
    """, (match_id,))

    # удаляем матч
    cursor.execute("""
    DELETE FROM matches
    WHERE id = ?
    """, (match_id,))

    conn.commit()

    await bot.send_message(
        message.from_user.id,
        f"Матч #{match_id} удален."
    )

    await safe_delete(message)

#  /REMOVEPLAYER command
@dp.message(Command("removeplayer"))
async def removeplayer_handler(message: Message):

    await safe_delete(message)

    if not is_admin(message.from_user.id):
        return

    match_id = get_active_match_id()

    if match_id is None:
        await bot.send_message(
            message.from_user.id,
            "Нет активного матча."
        )
        return

    parts = message.text.split()

    if len(parts) < 2:
        await bot.send_message(
            message.from_user.id,
            "Использование:\n/removeplayer Мурзинов"
        )
        return

    player_name = parts[1].strip().title()

    player_id = get_player_id(player_name)

    if player_id is None:
        await bot.send_message(
            message.from_user.id,
            "Игрок не найден."
        )
        return

    cursor.execute("""
    SELECT *
    FROM match_players
    WHERE match_id = ?
    AND player_id = ?
    """, (match_id, player_id))

    exists = cursor.fetchone()

    if not exists:
        await bot.send_message(
            message.from_user.id,
            f"{player_name} не участвует в матче."
        )
        return

    cursor.execute("""
    DELETE FROM match_players
    WHERE match_id = ?
    AND player_id = ?
    """, (match_id, player_id))



    conn.commit()

    await bot.send_message(
        message.from_user.id,
        f"❌ {player_name} удален из матча."
    )

#  /MATCHDETAILS command
@dp.message(Command("matchdetails"))
async def matchdetails_handler(message: Message):

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/matchdetails <match_id>"
        )
        return

    try:
        match_id = int(parts[1])

    except ValueError:
        await message.answer("ID матча должен быть числом.")
        return

    # матч
    cursor.execute("""
    SELECT
        id,
        match_date,
        red_score,
        green_score,
        winner
    FROM matches
    WHERE id = ?
    """, (match_id,))

    match_data = cursor.fetchone()

    if not match_data:
        await message.answer("Матч не найден.")
        return

    # игроки матча
    cursor.execute("""
    SELECT
        p.name,
        mp.team
    FROM match_players mp
    JOIN players p
        ON mp.player_id = p.id
    WHERE mp.match_id = ?
    """, (match_id,))

    players_data = cursor.fetchall()

    # голы
    cursor.execute("""
    SELECT
        p.name,
        COUNT(g.id)
    FROM goals g
    JOIN players p
        ON g.scorer_id = p.id
    WHERE g.match_id = ?
    GROUP BY p.name
    """, (match_id,))

    goals_data = cursor.fetchall()

    # словарь голов
    goals_dict = {}

    for name, goals in goals_data:
        goals_dict[name] = goals

    red_team = []
    green_team = []

    for name, team in players_data:

        goals = goals_dict.get(name, 0)

        ball_icons = " ⚽" * goals if goals > 0 else ""

        player_line = f"• {name}{ball_icons}"

        if team == "red":
            red_team.append(player_line)

        else:
            green_team.append(player_line)

    text = (
        f"🏆 Матч #{match_data[0]}\n"
        f"📅 {match_data[1]}\n\n"
        f"🔴 {match_data[2]} - {match_data[3]} 🟢\n\n"
    )

    text += "🔴 Красные:\n"
    text += "\n".join(red_team)

    text += "\n\n🟢 Зеленые:\n"
    text += "\n".join(green_team)

    await message.answer(text)