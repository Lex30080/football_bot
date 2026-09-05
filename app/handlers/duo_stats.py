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

# 1. chemistry(player)


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


# 2. duo(player1, player2)
@dp.message(Command("duo"))
async def duo_handler(message: Message, command: CommandObject):

    if not command.args:
        await message.answer(
            "Использование:\n"
            "/duo Игрок1 Игрок2"
        )
        return

    parts = command.args.split()

    if len(parts) < 2:
        await message.answer(
            "Нужно указать двух игроков:\n"
            "/duo Игрок1 Игрок2"
        )
        return

    player1 = parts[0].strip().lower()
    player2 = parts[1].strip().lower()

    if player1 == player2:
        await message.answer("Нужно указать двух разных игроков.")
        return

    pair_stats = build_pair_statistics()

    found_pair = None
    found_stats = None

    for pair, stats in pair_stats.items():

        pair_lower = (
            pair[0].strip().lower(),
            pair[1].strip().lower()
        )

        if set(pair_lower) == {player1, player2}:
            found_pair = pair
            found_stats = stats
            break

    if not found_pair:
        await message.answer(
            "Эта связка не найдена."
        )
        return

    games = found_stats["games"]

    if games < 1:
        await message.answer(
            "Недостаточно данных "
            "(минимум 1 совместный матч)."
        )
        return

    wins = found_stats["wins"]
    draws = found_stats["draws"]
    losses = found_stats["losses"]

    goals_for = found_stats["goals_for"]
    goals_against = found_stats["goals_against"]

    winrate = wins * 100 / games
    goal_diff = goals_for - goals_against

    text = (
        "🤝 <b>DUO</b>\n\n"
        f"<b>{found_pair[0]} + {found_pair[1]}</b>\n\n"
        f"🏆 Winrate     {winrate:.1f}%\n"
        f"🎮 Матчей      {games}\n"
        f"✅ Побед       {wins}\n"
        f"🤝 Ничьих      {draws}\n"
        f"❌ Поражений   {losses}\n\n"
        f"⚽ Забито      {goals_for}\n"
        f"🥅 Пропущено   {goals_against}\n"
        f"📈 Разница     {goal_diff:+d}"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# 3. top_duo_wins(limit)
@dp.message(Command("topduowins"))
async def top_duo_wins_handler(
    message: Message,
    command: CommandObject
):

    # По умолчанию показываем ТОП-5
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        # Минимум 3 совместных матча
        if stats["games"] < 3:
            continue

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "wins": stats["wins"],
            "winrate": stats["wins"] * 100 / stats["games"]
        })

    duos.sort(
        key=lambda x: (
            x["wins"],
            x["winrate"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer(
            "Недостаточно данных."
        )
        return

    text = "🏆 <b>ТОП DUO ПО ПОБЕДАМ</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   🏆 {duo['wins']} побед · "
            f"WR {duo['winrate']:.0f}% · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# топ по поражениям
@dp.message(Command("topduolosses"))
async def top_duo_losses_handler(
    message: Message,
    command: CommandObject
):

    # По умолчанию показываем ТОП-5
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        # Минимум 3 совместных матча
        if stats["games"] < 3:
            continue

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "losses": stats["losses"],
            "winrate": stats["wins"] * 100 / stats["games"]
        })

    duos.sort(
        key=lambda x: (
            x["losses"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer(
            "Недостаточно данных."
        )
        return

    text = "❌ <b>ТОП DUO ПО ПОРАЖЕНИЯМ</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   ❌ {duo['losses']} поражений · "
            f"WR {duo['winrate']:.0f}% · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# топ по забитым голам
@dp.message(Command("topduogoals"))
async def top_duo_goals_handler(
    message: Message,
    command: CommandObject
):

    # По умолчанию показываем ТОП-5
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        # Минимум 3 совместных матча
        if stats["games"] < 3:
            continue

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "goals_for": stats["goals_for"],
            "goals_against": stats["goals_against"]
        })

    duos.sort(
        key=lambda x: (
            x["goals_for"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer(
            "Недостаточно данных."
        )
        return

    text = "⚽ <b>ТОП DUO ПО ЗАБИТЫМ ГОЛАМ</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   ⚽ {duo['goals_for']} голов · "
            f"🥅 {duo['goals_against']} пропущено · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# топ по пропущеным голам
@dp.message(Command("topduogoalsagainst"))
async def top_duo_goals_against_handler(
    message: Message,
    command: CommandObject
):

    # По умолчанию показываем ТОП-5
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        # Минимум 3 совместных матча
        if stats["games"] < 3:
            continue

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "goals_against": stats["goals_against"],
            "goals_for": stats["goals_for"]
        })

    duos.sort(
        key=lambda x: (
            x["goals_against"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer(
            "Недостаточно данных."
        )
        return

    text = "🥅 <b>ТОП DUO ПО ПРОПУЩЕННЫМ ГОЛАМ</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   🥅 {duo['goals_against']} пропущено · "
            f"⚽ {duo['goals_for']} забито · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# топ по разнице голов
@dp.message(Command("topduodiff"))
async def top_duo_diff_handler(
    message: Message,
    command: CommandObject
):

    # По умолчанию показываем ТОП-5
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        # Минимум 3 совместных матча
        if stats["games"] < 3:
            continue

        goal_diff = (
            stats["goals_for"]
            - stats["goals_against"]
        )

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "goals_for": stats["goals_for"],
            "goals_against": stats["goals_against"],
            "goal_diff": goal_diff
        })

    duos.sort(
        key=lambda x: (
            x["goal_diff"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer(
            "Недостаточно данных."
        )
        return

    text = "📈 <b>ТОП DUO ПО РАЗНИЦЕ ГОЛОВ</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   📈 {duo['goal_diff']:+d} · "
            f"⚽ {duo['goals_for']} : "
            f"{duo['goals_against']} · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# топ дуо по голам за матч
@dp.message(Command("topduoaverage"))
async def top_duo_average_handler(
    message: Message,
    command: CommandObject
):

    # По умолчанию показываем ТОП-5
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        # Минимум 3 совместных матча
        if stats["games"] < 3:
            continue

        average_goals = (
            stats["goals_for"] / stats["games"]
        )

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "goals_for": stats["goals_for"],
            "goals_against": stats["goals_against"],
            "average_goals": average_goals
        })

    duos.sort(
        key=lambda x: (
            x["average_goals"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer(
            "Недостаточно данных."
        )
        return

    text = "⚽ <b>ТОП DUO ПО СРЕДНИМ ГОЛАМ</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   ⚽ {duo['average_goals']:.2f} за матч · "
            f"{duo['goals_for']} забито · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

@dp.message(Command("topduo"))
async def top_duo_handler(
    message: Message,
    command: CommandObject
):
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        if stats["games"] < 3:
            continue

        winrate = stats["wins"] * 100 / stats["games"]

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "wins": stats["wins"],
            "winrate": winrate
        })

    duos.sort(
        key=lambda x: (
            x["winrate"],
            x["wins"],
            x["games"]
        ),
        reverse=True
    )

    duos = duos[:limit]

    if not duos:
        await message.answer("Недостаточно данных.")
        return

    text = "🤝 <b>ТОП DUO ПО WINRATE</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   🏆 {duo['wins']} побед · "
            f"WR {duo['winrate']:.0f}% · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(text, parse_mode="HTML")

@dp.message(Command("topduoworst"))
async def top_duo_worst_handler(
    message: Message,
    command: CommandObject
):
    limit = 5

    if command.args:
        try:
            limit = int(command.args)
        except ValueError:
            pass

    pair_stats = build_pair_statistics()

    duos = []

    for pair, stats in pair_stats.items():

        if stats["games"] < 3:
            continue

        winrate = stats["wins"] * 100 / stats["games"]

        duos.append({
            "pair": pair,
            "games": stats["games"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "winrate": winrate
        })

    duos.sort(
        key=lambda x: (
            x["winrate"],
            -x["losses"],
            -x["games"]
        )
    )

    duos = duos[:limit]

    if not duos:
        await message.answer("Недостаточно данных.")
        return

    text = "💀 <b>ХУДШИЕ DUO ПО WINRATE</b>\n\n"

    for i, duo in enumerate(duos, 1):

        text += (
            f"{i}. {duo['pair'][0]} + {duo['pair'][1]}\n"
            f"   💀 {duo['losses']} поражений · "
            f"WR {duo['winrate']:.0f}% · "
            f"GP {duo['games']}\n\n"
        )

    await message.answer(text, parse_mode="HTML")