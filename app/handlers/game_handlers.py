import random
from aiogram.filters import Command
from aiogram.types import Message, PollAnswer
from app.database.db import conn, cursor
from aiogram.exceptions import TelegramBadRequest  

from app.bot import dp, bot
from app.state.game_state import game_state, MIN_PLAYERS, MAX_PLAYERS
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



#  /GAME command
@dp.message(Command("game"))
async def game_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    if not game_state.game_active:
        game_state.game_active = True
        game_state.players_for_game = []
        await message.answer("Новая игра началась! нажми /join чтобы записаться")
    else:
        await message.answer(f"Набор уже идет! {len(game_state.players_for_game)}/{MAX_PLAYERS} игроков записано")    

# /JOIN command (NEEDS CORRECTING LATER)
@dp.message(Command("join"))
async def join_handler(message: Message):
   if not game_state.game_active:
        await message.answer("❌ Сейчас нет активной игры.\nИспользуйте /game")
        return
   if len(game_state.players_for_game) >= MAX_PLAYERS:
        await message.answer("Мест нет, 12/12")
        return 
   
   parts = message.text.split()
   name = parts[1].strip().title()
   
   if name not in game_state.players_for_game:
       game_state.players_for_game.append(name)
       status = get_game_status()
       await message.answer(status)
   else:
       await message.answer(f"{name} уже записан на игру.")

#  /LINEUP command
@dp.message(Command("lineup"))
async def lineup_handler(message: Message):
    await safe_delete(message)
    if not game_state.game_active:
        await bot.send_message(message.from_user.id, "Сейчас нет активной игры.\nИспользуйте /game")
        return
    await bot.send_message(message.from_user.id, format_lineup(game_state.players_for_game))


# /CANCEL command
@dp.message(Command("cancel"))
async def cancel_handler(message: Message):
    await safe_delete(message)
    if not is_admin(message.from_user.id):
        return
    
    if not game_state.game_active:
        await message.answer("Сейчас нет активной игры.")
        return
    game_state.game_active = False
    game_state.players_for_game = []
    await message.answer("Игра отменена.")


# /LEAVE command
@dp.message(Command("leave"))
async def leave_handler(message: Message):

    if not game_state.game_active:
        await message.answer("Сейчас нет активной игры.")
        return

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("Использование: /leave Фамилия")
        return

    name = parts[1].strip().title()

    if name in game_state.players_for_game:
        game_state.players_for_game.remove(name)

        status = get_game_status()

        await message.answer(
            f"{name} покинул игру.\n\n{status}"
        )

    else:
        await message.answer(
            f"{name} не записан на игру."
        )

# /POLL command
@dp.message(Command("poll"))
async def poll_handler(message: Message):
    if len(message.text.split()) < 2:
        await message.answer("Использование: /poll <вариант1> <вариант2> ...")
        return
    parts = message.text.split()
    parts.append("Пас")
    await message.answer_poll(question="Когда играем?", options=parts[1:], is_anonymous=False, allows_multiple_answers=True)
    
    game_state.poll_options = parts[1:]
    game_state.poll_votes = {}
    for option in game_state.poll_options:
        game_state.poll_votes[option] = []
    
@dp.poll_answer()
async def poll_answer_handler(poll_answer: PollAnswer):
    name = poll_answer.user.first_name
    for index, option in enumerate(game_state.poll_options):
        if index in poll_answer.option_ids:
            if name not in game_state.poll_votes[option]:
                game_state.poll_votes[option].append(name)
        else:
            if name in game_state.poll_votes[option]:
                game_state.poll_votes[option].remove(name)

# /ACTIVATE_GAME
@dp.message(Command("activate_game"))
async def activate_game_handler(message: Message):
    await safe_delete(message)
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await bot.send_message(message.from_user.id, "Использование: /activate_game <dd.mm>")
        return
    
    date = parts[1]
        
        
    if date not in game_state.poll_votes:
        await bot.send_message(message.from_user.id, f"Проверьте дату")
        return
    game_state.players_for_game = game_state.poll_votes[date].copy()
    if len(game_state.players_for_game) < MIN_PLAYERS:
        await bot.send_message(message.from_user.id, f"Недостаточно игроков для начала игры.")
        game_state.game_active = False
        return
    else:
        game_state.game_active = True
        status = get_game_status()
        await message.answer(f"Игра активирована на {date}!\n\nИспользуйте /join чтобы записаться\n\n")
        await message.answer(status)  
        await message.answer(format_lineup(game_state.players_for_game))

# /TEAMS command
@dp.message(Command("teams"))
async def teams_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    active_match_id = get_active_match_id()

    if active_match_id is not None:
        await message.answer("Матч уже создан.")
        return

    if not game_state.game_active:
        await message.answer("Сейчас нет активной игры.")
        return

    if len(game_state.players_for_game) < MIN_PLAYERS:
        await message.answer("Недостаточно игроков.")
        return

    game_state.current_red_team = []
    game_state.current_green_team = []

    shuffled_players = game_state.players_for_game.copy()
    random.shuffle(shuffled_players)

    sorted_players = sorted(
        shuffled_players,
        key=lambda player: get_player_rating(player),
        reverse=True
    )

    red_team = []
    green_team = []

    for i, player in enumerate(sorted_players):

        if i % 2 == 0:
            red_team.append(player)
        else:
            green_team.append(player)

    game_state.current_red_team = red_team.copy()
    game_state.current_green_team = green_team.copy()

    cursor.execute("""
    UPDATE matches
    SET is_active = 0
    WHERE is_active = 1
    """)

    cursor.execute("""
    INSERT INTO matches (
        match_date,
        is_active
    )
    VALUES (
        DATETIME('now'),
        1
    )
    """)

    conn.commit()

    new_match_id = cursor.lastrowid
    game_state.current_match_id = new_match_id

    for player in red_team:

        player_id = get_player_id(player)

        cursor.execute("""
        INSERT INTO match_players (
            match_id,
            player_id,
            team
        )
        VALUES (?, ?, ?)
        """, (new_match_id, player_id, "red"))

    for player in green_team:

        player_id = get_player_id(player)

        cursor.execute("""
        INSERT INTO match_players (
            match_id,
            player_id,
            team
        )
        VALUES (?, ?, ?)
        """, (new_match_id, player_id, "green"))

    conn.commit()

    text = "Команды:\n\n"

    text += "🔴 Красные:\n"

    for player in red_team:
        text += f"• {player}\n"

    text += "\n🟢 Зеленые:\n"

    for player in green_team:
        text += f"• {player}\n"

    await message.answer(text)
 

# /FINISH command
@dp.message(Command("finish"))
async def finish_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    match_id = get_active_match_id()

    if match_id is None:
        await message.answer("Нет активного матча.")
        return

    cursor.execute("""
    SELECT status
    FROM matches
    WHERE id = ?
    """, (match_id,))

    match_result = cursor.fetchone()

    if not match_result:
        await message.answer("Матч не найден.")
        return

    if match_result[0] != "active":
        await message.answer("Матч уже завершен.")
        return

    parts = message.text.split()

    if len(parts) < 3:
        await message.answer(
            "Использование: /finish <red_score> <green_score>"
        )
        return

    try:
        red_score = int(parts[1])
        green_score = int(parts[2])

    except ValueError:
        await message.answer("Счет должен быть числом")
        return

    if red_score > green_score:
        winner = "red"

    elif green_score > red_score:
        winner = "green"

    else:
        winner = "draw"

    cursor.execute("""
    UPDATE matches
    SET red_score = ?,
        green_score = ?,
        winner = ?,
        status = 'awaiting goals',
        is_active = 1
    WHERE id = ?
    """, (red_score, green_score, winner, match_id))

    conn.commit()

    game_state.game_active = False

    await message.answer(
        f"Матч завершен!\n"
        f"🔴 {red_score} - {green_score} 🟢"
    )

#  /SCORED command
@dp.message(Command("scored"))
async def scored_handler(message: Message):
    await safe_delete(message)
    if not is_admin(message.from_user.id):
        return
    
    match_id = get_active_match_id()
    if match_id is None:
        await bot.send_message(message.from_user.id, "Нет активного матча.")
        return
    
    cursor.execute("""
    SELECT status
    FROM matches
    WHERE id = ?
    """, (match_id,))

    match_status = cursor.fetchone()

    if not match_status:
        await bot.send_message(
            message.from_user.id,
            "Матч не найден."
        )
        return

    if match_status[0] != "awaiting goals":
        await bot.send_message(
            message.from_user.id,
            "Сначала нужно завершить матч через /finish"
        )
        return

    cursor.execute("""
    SELECT COUNT(*)
    FROM goals
    WHERE match_id = ?
    """, (match_id,))

    goals_already_added = cursor.fetchone()[0]

    if goals_already_added > 0:
        await bot.send_message(message.from_user.id, "Голы для этого матча уже внесены.")
        return
    parts = message.text.split()

    if len(parts) < 3 or len(parts[1:]) % 2 != 0:
        await bot.send_message(message.from_user.id,
            "Использование:\n/scored Murzinov 4 Novikov 2"
        )
        return
    goal_data = []
    added_goals = 0

    for i in range(1, len(parts), 2):

        scorer = parts[i].strip().title()

        try:
            goals_count = int(parts[i + 1])
        except ValueError:
            await bot.send_message(message.from_user.id, f"Ошибка в количестве голов у {scorer}")
            return

        player_id = get_player_id(scorer)

        if player_id is None:
            await bot.send_message(
                message.from_user.id,
                f"Игрок {scorer} не найден."
                )
            return

        cursor.execute("""
        SELECT team
        FROM match_players
        WHERE match_id = ?
        AND player_id = ?
        """, (match_id, player_id))

        team_result = cursor.fetchone()

        if not team_result:
            await bot.send_message(message.from_user.id, f"{scorer} не играл в матче.")
            return

        team = team_result[0]
    

        goal_data.append((player_id, team, goals_count))
        added_goals += goals_count


    cursor.execute("""
    SELECT red_score, green_score
    FROM matches
    WHERE id = ?
    """, (match_id,))

    match_data = cursor.fetchone()

    expected_goals = match_data[0] + match_data[1]

    if added_goals != expected_goals:
        await bot.send_message(message.from_user.id, 
            f"⚠️ Несовпадение!\n"
            f"Счет матча: {expected_goals} голов\n"
            f"Внесено голов: {added_goals}"
        )
        return


    for player_id, team, goals_count in goal_data:
        for _ in range(goals_count):
            cursor.execute("""
            INSERT INTO goals (match_id, scorer_id, team)
            VALUES (?, ?, ?)
            """, (match_id, player_id, team))

    conn.commit()
    
    
    cursor.execute("""
    UPDATE matches
    SET status = 'finished',
        is_active = 0
    WHERE id = ?
    """, (match_id,))

    conn.commit()

    
    game_state.current_red_team = []
    game_state.current_green_team = []
    game_state.players_for_game = []

    await bot.send_message(message.from_user.id, f"⚽ Добавлено голов: {added_goals}")
