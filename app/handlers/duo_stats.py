from collections import defaultdict
from itertools import combinations

from app.database.db import cursor
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.filters.command import CommandObject

from app.bot import dp


def build_pair_statistics():

    pair_stats = defaultdict(lambda: {
        "games": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
    })

    cursor.execute("""
        SELECT id,
               red_score,
               green_score,
               winner
        FROM matches
        WHERE status = 'finished'
    """)

    matches = cursor.fetchall()

    for match_id, red_score, green_score, winner in matches:

        cursor.execute("""
            SELECT p.name,
                   mp.team
            FROM match_players mp
            JOIN players p
                ON p.id = mp.player_id
            WHERE mp.match_id = ?
        """, (match_id,))

        rows = cursor.fetchall()

        red_team = []
        green_team = []

        for name, team in rows:

            if team == "red":
                red_team.append(name)
            else:
                green_team.append(name)

        # ---------- Красная команда ----------

        for pair in combinations(red_team, 2):

            pair = tuple(sorted(pair))

            stats = pair_stats[pair]

            stats["games"] += 1
            stats["goals_for"] += red_score
            stats["goals_against"] += green_score

            if winner == "red":
                stats["wins"] += 1
            elif winner == "draw":
                stats["draws"] += 1
            else:
                stats["losses"] += 1

        # ---------- Зеленая команда ----------

        for pair in combinations(green_team, 2):

            pair = tuple(sorted(pair))

            stats = pair_stats[pair]

            stats["games"] += 1
            stats["goals_for"] += green_score
            stats["goals_against"] += red_score

            if winner == "green":
                stats["wins"] += 1
            elif winner == "draw":
                stats["draws"] += 1
            else:
                stats["losses"] += 1

    return pair_stats

# 2. chemistry(player)


@dp.message(Command("chemistry"))
async def chemistry_handler(message: Message, command: CommandObject):

    if not command.args:
        await message.answer(
            "Использование:\n"
            "/chemistry Игрок [количество]"
        )
        return

    parts = command.args.split()

    player = parts[0].lower()

    # По умолчанию показываем ТОП-3 связки
    limit = 3

    if len(parts) > 1:
        try:
            limit = int(parts[1])
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    

    chemistry = []

    for pair, stats in pair_stats.items():

        pair_lower = (pair[0].lower(), pair[1].lower())
        
        if player not in pair_lower:
            continue

        if pair[0].lower() == player:
            teammate = pair[1]
        else:
            teammate = pair[0]

        games = stats["games"]

        # Минимум 4 совместных матча
        if games < 3:
            continue

        winrate = stats["wins"] * 100 / games
        goal_diff = stats["goals_for"] - stats["goals_against"]

        chemistry.append({
            "name": teammate,
            "games": games,
            "wins": stats["wins"],
            "draws": stats["draws"],
            "losses": stats["losses"],
            "goals_for": stats["goals_for"],
            "goals_against": stats["goals_against"],
            "goal_diff": goal_diff,
            "winrate": winrate
        })

    if not chemistry:
        await message.answer(
            "Недостаточно данных (минимум 4 совместных матча)."
        )
        return

    chemistry.sort(
        key=lambda x: (
            x["winrate"],
            x["games"]
        ),
        reverse=True
    )

    chemistry = chemistry[:limit]

    text = (
        f"🧪 <b>Химия игрока {player}</b>\n\n"
        "<pre>"
    )

    text += (
        f"{'Игрок':9}"
        f"{'WR%':>6}"
        f"{'GP':>5}"
        f"{'GS':>5}"
        f"{'GA':>5}"
        f"{'GD':>6}\n"
    )

    text += "-" * 36 + "\n"

    for row in chemistry:

        name = row["name"]

        if len(name) > 9:
            name = name[:8] + "…"

        text += (
            f"{name:9}"
            f"{row['winrate']:>6.1f}"
            f"{row['games']:>5}"
            f"{row['goals_for']:>5}"
            f"{row['goals_against']:>5}"
            f"{row['goal_diff']:>6}\n"
        )

    text += "</pre>"

    await message.answer(
        text,
        parse_mode="HTML"
    )

"""
3. duo(player1, player2)

4. top_duo_wins(limit)

5. top_duo_goals(limit)

6. top_duo_diff(limit)

7. хендлеры
"""