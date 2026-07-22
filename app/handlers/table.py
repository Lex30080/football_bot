from app.database.db import cursor
from aiogram.exceptions import TelegramBadRequest
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot import dp

def get_players_table():

    cursor.execute("""
        SELECT id, name
        FROM players
        ORDER BY name
    """)

    players = cursor.fetchall()

    result = []

    for player_id, name in players:

        # Голы
        cursor.execute("""
            SELECT COUNT(*)
            FROM goals
            WHERE scorer_id = ?
        """, (player_id,))
        goals = cursor.fetchone()[0]

        # Матчи
        cursor.execute("""
            SELECT COUNT(*)
            FROM match_players mp
            JOIN matches m
                ON mp.match_id = m.id
            WHERE mp.player_id = ?
            AND m.status = 'finished'
        """, (player_id,))
        games = cursor.fetchone()[0]

        # Победы
        cursor.execute("""
            SELECT COUNT(*)
            FROM match_players mp
            JOIN matches m
                ON mp.match_id = m.id
            WHERE mp.player_id = ?
            AND (
                (mp.team='red' AND m.winner='red')
                OR
                (mp.team='green' AND m.winner='green')
            )
        """, (player_id,))
        wins = cursor.fetchone()[0]

        # Ничьи
        cursor.execute("""
            SELECT COUNT(*)
            FROM match_players mp
            JOIN matches m
                ON mp.match_id = m.id
            WHERE mp.player_id = ?
            AND m.winner='draw'
        """, (player_id,))
        draws = cursor.fetchone()[0]

        losses = games - wins - draws

        points = wins * 3 + draws

        if games == 0:
            continue
        
        result.append({
            "name": name,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "games": games,
            "goals": goals,
            "points": points
        })

    return result

def build_table(sort_by="wins"):

    players = get_players_table()

    if sort_by == "points":
        players.sort(
        key=lambda x: (
            x["points"],
            x["wins"],
            x["goals"]
        ),
        reverse=True
    )
    else:
        players.sort(
        key=lambda x: x[sort_by],
        reverse=True
    )

    text = (
        "📊 <b>Таблица игроков</b>\n\n"
        "<pre>"
        f"{'№':<3}"
        f"{'Игрок':<14}"
        f"{'W':>3}"
        f"{'D':>3}"
        f"{'L':>3}"
        f"{'GP':>4}"
        f"{'G':>4}"
        f"{'Pts':>5}\n"
        + "-" * 42 + "\n"
    )

    for i, p in enumerate(players, start=1):

        text += (
            f"{i:<3}"
            f"{p['name']:<14}"
            f"{p['wins']:>3}"
            f"{p['draws']:>3}"
            f"{p['losses']:>3}"
            f"{p['games']:>4}"
            f"{p['goals']:>4}"
            f"{p['points']:>5}\n"
        )

    text += "</pre>"

    return text

def table_keyboard(current_sort="wins"):

    labels = {
        "points": "📊 Points",
        "wins": "🏆 Wins",
        "draws": "🤝 Draws",
        "losses": "❌ Losses",
        "games": "🎮 Games",
        "goals": "⚽ Goals"
    }

    kb = InlineKeyboardBuilder()

    for key, text in labels.items():

        if key == current_sort:
            text += " ▼"

        kb.button(
            text=text,
            callback_data=f"table:{key}"
        )

    kb.adjust(3, 2)

    return kb.as_markup()

@dp.message(Command("table"))
async def show_table(message: Message):

    await message.answer(
        build_table("points"),
        parse_mode="HTML",
        reply_markup=table_keyboard("points")
    )

@dp.callback_query(F.data.startswith("table:"))
async def table_sort(callback: CallbackQuery):

    sort_by = callback.data.split(":")[1]

    try:
        await callback.message.edit_text(
            build_table(sort_by),
            parse_mode="HTML",
            reply_markup=table_keyboard(sort_by)
        )
    except TelegramBadRequest:
        pass

    await callback.answer()



