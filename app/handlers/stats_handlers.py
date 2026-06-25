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


# player /STATS command
@dp.message(Command("stats"))
async def stats_handler(message: Message):
    await safe_delete(message)
    parts = message.text.split()

    # проверка аргумента
    if len(parts) < 2:
        await bot.send_message(message.from_user.id,
            "Использование:\n/stats Фамилия"
        )
        return

    player_name = parts[1].strip().title()

    # получаем player_id
    player_id = get_player_id(player_name)

    if player_id is None:
        await bot.send_message(message.from_user.id, "Игрок не найден.")
        return

    # =========================
    # МАТЧИ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM match_players
    WHERE player_id = ?
    """, (player_id,))

    matches = cursor.fetchone()[0]

    # =========================
    # ГОЛЫ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM goals
    WHERE scorer_id = ?
    """, (player_id,))

    goals = cursor.fetchone()[0]

    # =========================
    # ПОБЕДЫ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM matches m
    JOIN match_players mp
        ON m.id = mp.match_id
    WHERE mp.player_id = ?
    AND (
        (mp.team = 'red' AND m.winner = 'red')
        OR
        (mp.team = 'green' AND m.winner = 'green')
    )
    """, (player_id,))

    wins = cursor.fetchone()[0]

    # =========================
    # ПОРАЖЕНИЯ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM matches m
    JOIN match_players mp
        ON m.id = mp.match_id
    WHERE mp.player_id = ?
    AND (
        (mp.team = 'red' AND m.winner = 'green')
        OR
        (mp.team = 'green' AND m.winner = 'red')
    )
    """, (player_id,))

    losses = cursor.fetchone()[0]

    # =========================
    # НИЧЬИ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM matches m
    JOIN match_players mp
        ON m.id = mp.match_id
    WHERE mp.player_id = ?
    AND m.winner = 'draw'
    """, (player_id,))

    draws = cursor.fetchone()[0]

    # =========================
    # ДОП. СТАТИСТИКА
    # =========================

    goals_per_game = 0
    winrate = 0

    if matches > 0:
        goals_per_game = round(goals / matches, 2)
        winrate = round((wins / matches) * 100, 1)

    # =========================
    # ХЕТ-ТРИКИ
    # =========================

    cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT match_id
        FROM goals
        WHERE scorer_id = ?
        GROUP BY match_id
        HAVING COUNT(*) >= 3
    )
    """, (player_id,))

    hattricks = cursor.fetchone()[0]
    
    # =========================
    # ОТВЕТ
    # =========================
    text = (
    f"📊 Статистика игрока {player_name}\n\n"

    f"🎮 Матчей: {matches}\n"
    f"⚽ Голов: {goals}\n"
    f"📈 Голов за матч: {goals_per_game}\n"
    f"🎩 Хет-трики: {hattricks}\n\n"

    f"🏆 Побед: {wins}\n"
    f"❌ Поражений: {losses}\n"
    f"🤝 Ничьих: {draws}\n"
    f"📊 Winrate: {winrate}%"
)

    await bot.send_message(message.from_user.id, text)


@dp.message(Command("matches"))
async def list_matches(message: Message):

    # -----------------------
    # parse argument
    # -----------------------
    args = message.text.split()

    limit = 5  # default

    if len(args) > 1:
        if args[1].isdigit():
            limit = int(args[1])

    # защита от слишком больших запросов
    if limit > 50:
        limit = 50

    # -----------------------
    # query DB
    # -----------------------
    cursor.execute("""
        SELECT id, match_date, red_score, green_score
        FROM matches
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    if not rows:
        await message.answer("Матчей пока нет")
        return

    # -----------------------
    # output
    # -----------------------
    text = ""

    for match_id, date, red, green in rows:
        text += f"Матч ID {match_id} {date} {red}-{green}\n"

    await message.answer(text)

def build_match_info(match_id):

    cursor.execute("""
    SELECT match_date, red_score, green_score
    FROM matches
    WHERE id = ?
    """, (match_id,))

    match_data = cursor.fetchone()

    if not match_data:
        return "Матч не найден."

    match_date, red_score, green_score = match_data

    cursor.execute("""
    SELECT p.name, mp.team
    FROM match_players mp
    JOIN players p
        ON p.id = mp.player_id
    WHERE mp.match_id = ?
    """, (match_id,))

    players_data = cursor.fetchall()

    red_team = []
    green_team = []

    for name, team in players_data:
        if team == "red":
            red_team.append(name)
        else:
            green_team.append(name)

    cursor.execute("""
    SELECT p.name, COUNT(*)
    FROM goals g
    JOIN players p
        ON p.id = g.scorer_id
    WHERE g.match_id = ?
    GROUP BY p.name
    """, (match_id,))

    scorers = {
        name: goals
        for name, goals in cursor.fetchall()
    }

    text = (
        f"📅 {match_date}\n"
        f"🆔 Матч ID {match_id}\n\n"
        f"🔴 {red_score} : {green_score} 🟢\n\n"
    )

    text += "🔴 Красные:\n"

    for player in red_team:
        balls = "⚽" * scorers.get(player, 0)
        text += f"• {player} {balls}\n"

    text += "\n🟢 Зеленые:\n"

    for player in green_team:
        balls = "⚽" * scorers.get(player, 0)
        text += f"• {player} {balls}\n"

    return text

@dp.message(Command("match"))
async def matchinfo_handler(message: Message):

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/match <id>"
        )
        return

    match_id = int(parts[1])

    await message.answer(
        build_match_info(match_id)
    )

@dp.message(Command("lastmatch"))
async def lastmatch_handler(message: Message):

    cursor.execute("""
    SELECT id
    FROM matches
    ORDER BY id DESC
    LIMIT 1
    """)

    result = cursor.fetchone()

    if not result:
        await message.answer("Матчей пока нет.")
        return

    await message.answer(
        build_match_info(result[0])
    )


@dp.message(Command("topmatches"))
async def top_matches(message: Message):

    # аргумент после команды
    parts = message.text.split()

    limit = 10  # по умолчанию

    if len(parts) > 1:
        if parts[1].isdigit():
            limit = int(parts[1])
        else:
            await message.answer("❌ Укажи число, например: /topmatches 5")
            return

    cursor.execute("""
        SELECT
            p.name,
            COUNT(mp.match_id) as matches_count
        FROM players p
        LEFT JOIN match_players mp ON mp.player_id = p.id
        GROUP BY p.id
        ORDER BY matches_count DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    if not rows:
        await message.answer("Нет данных")
        return

    text = f"🏆 ТОП {limit} игроков по матчам:\n\n"

    for i, (name, count) in enumerate(rows, start=1):
        text += f"{i}. {name} — {count}\n"

    await message.answer(text)

def get_player_name(player_id: int):
    cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
    row = cursor.fetchone()
    return row[0] if row else "Неизвестный"


@dp.message(Command("general"))
async def general(message: Message):

    # =========================
    # ОБЩАЯ СТАТИСТИКА
    # =========================

    cursor.execute("SELECT COUNT(*) FROM matches")
    total_matches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM goals")
    total_goals = cursor.fetchone()[0]

    # =========================
    # САМЫЙ РЕЗУЛЬТАТИВНЫЙ МАТЧ
    # =========================
    cursor.execute("""
        SELECT id, match_date, red_score, green_score
        FROM matches
        ORDER BY (red_score + green_score) DESC
        LIMIT 1
    """)
    best_match = cursor.fetchone()

    best_match_text = (
        f"ID {best_match[0]} {best_match[1]} {best_match[2]}-{best_match[3]}"
        if best_match else "Нет данных"
    )

       # =========================
    # ТОП БОМБАРДИРЫ
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM goals
        GROUP BY scorer_id
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        max_goals = row[0]

        cursor.execute("""
            SELECT scorer_id, COUNT(*) as goals_count
            FROM goals
            GROUP BY scorer_id
            HAVING COUNT(*) = ?
            ORDER BY scorer_id
        """, (max_goals,))

        scorers = cursor.fetchall()

        top_scorer_text = "\n".join(
            f"{get_player_name(player_id)} — {goals_count}"
            for player_id, goals_count in scorers
        )
    else:
        top_scorer_text = "Нет данных"

    # =========================
    # ТОП ПО МАТЧАМ
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM match_players
        GROUP BY player_id
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        max_matches = row[0]

        cursor.execute("""
            SELECT player_id, COUNT(*) as matches_count
            FROM match_players
            GROUP BY player_id
            HAVING COUNT(*) = ?
            ORDER BY player_id
        """, (max_matches,))

        players_top = cursor.fetchall()

        top_player_text = "\n".join(
            f"{get_player_name(player_id)} — {matches_count}"
            for player_id, matches_count in players_top
        )
    else:
        top_player_text = "Нет данных"

    # =========================
    # РЕКОРД ГОЛОВ ЗА МАТЧ
    # =========================
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM goals
        GROUP BY scorer_id, match_id
        ORDER BY cnt DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        max_record = row[0]

        cursor.execute("""
            SELECT scorer_id, match_id, COUNT(*) as cnt
            FROM goals
            GROUP BY scorer_id, match_id
            HAVING COUNT(*) = ?
            ORDER BY match_id
        """, (max_record,))

        records = cursor.fetchall()

        record_text = "\n".join(
            f"{get_player_name(player_id)} — {cnt} (матч #{match_id})"
            for player_id, match_id, cnt in records
        )
    else:
        record_text = "Нет данных"


    # =========================
    # СРЕДНЯЯ РЕЗУЛЬТАТИВНОСТЬ
    # =========================
    cursor.execute("""
        SELECT AVG(red_score + green_score)
        FROM matches
    """)

    avg_goals = cursor.fetchone()[0]

    if avg_goals is None:
        avg_goals_text = "Нет данных"
    else:
        avg_goals_text = f"{avg_goals:.2f}"

    # =========================
    # САМЫЙ РАЗГРОМ
    # =========================
    cursor.execute("""
        SELECT id, match_date, red_score, green_score,
               ABS(red_score - green_score) as diff
        FROM matches
        ORDER BY diff DESC
        LIMIT 1
    """)
    blowout = cursor.fetchone()

    blowout_text = (
        f"#{blowout[0]} {blowout[1]} {blowout[2]}-{blowout[3]}"
        if blowout else "Нет данных"
    )

    # =========================
    # САМАЯ НИЧЬЯ
    # =========================
    cursor.execute("""
        SELECT id, match_date, red_score, green_score
        FROM matches
        WHERE red_score = green_score
        ORDER BY (red_score + green_score) DESC
        LIMIT 1
    """)
    draw = cursor.fetchone()

    draw_text = (
        f"#{draw[0]} {draw[1]} {draw[2]}-{draw[3]}"
        if draw else "Нет ничьих"
    )

    # =========================
    # ОТВЕТ
    # =========================
    await message.answer(
        "📊 ОБЩАЯ СТАТИСТИКА\n\n"
        "📌 Период: с мая 2026\n\n"

        f"⚽ Матчей: {total_matches}\n"
        f"🥅 Голов: {total_goals}\n\n"
        f"📈 Средняя результативность: {avg_goals_text} гола за матч\n\n"


        f"🔥 Топ бомбардир:\n{top_scorer_text}\n\n"

        f"🎮 Топ по матчам:\n{top_player_text}\n\n"

        f"🚀 Рекорд голов за матч:\n{record_text}\n\n"
        
        f"🏆 Самый результативный матч:\n{best_match_text}\n\n"

        f"💥 Самый большой разгром:\n{blowout_text}\n\n"

        f"🤝 Самая результативная ничья:\n{draw_text}"
    )


  