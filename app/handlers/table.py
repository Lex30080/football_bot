from app.database.db import cursor


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

        if games == 0:
            continue
        
        result.append({
            "name": name,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "games": games,
            "goals": goals
        })

    return result

def build_table(sort_by="wins"):

    players = get_players_table()

    players.sort(
        key=lambda x: x[sort_by],
        reverse=True
    )

    text = (
        "📊 <b>Таблица игроков</b>\n\n"
        "<pre>"
        "Игрок         W  D  L GP  G\n"
        "----------------------------\n"
    )

    for p in players:

        text += (
            f"{p['name'][:12]:12}"
            f"{p['wins']:>3}"
            f"{p['draws']:>3}"
            f"{p['losses']:>3}"
            f"{p['games']:>3}"
            f"{p['goals']:>4}\n"
        )

    text += "</pre>"

    return text

from aiogram.utils.keyboard import InlineKeyboardBuilder


def table_keyboard(current_sort="wins"):

    labels = {
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

from aiogram.filters import Command
from aiogram.types import Message

from app.bot import dp


@dp.message(Command("table"))
async def show_table(message: Message):

    await message.answer(
        build_table("wins"),
        parse_mode="HTML",
        reply_markup=table_keyboard("wins")
    )

from aiogram import F
from aiogram.types import CallbackQuery


@dp.callback_query(F.data.startswith("table:"))
async def table_sort(callback: CallbackQuery):

    sort_by = callback.data.split(":")[1]

    await callback.message.edit_text(
        build_table(sort_by),
        parse_mode="HTML",
        reply_markup=table_keyboard(sort_by)
    )

    await callback.answer()   