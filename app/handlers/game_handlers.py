import random
from aiogram.filters import Command
from aiogram.types import Message, PollAnswer
from app.database.db import conn, cursor
from aiogram.fsm.context import FSMContext

from app.bot import dp, bot
from app.state.game_state import game_state, MIN_PLAYERS, MAX_PLAYERS
from app.utils.helpers import (
    is_admin,
    get_player_id,
    get_player_rating,
    safe_delete,
    get_game_status,
    format_lineup
)
from app.data import players
from app.state.goal_input_fsm import GoalInputFSM
from app.handlers.goals_input_fsm import build_goals_kb

#=========================
# /GAME command
#=========================
@dp.message(Command("game"))
async def game_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    game_state.game_active = True
    game_state.players_for_game = []

    await message.answer(
        "⚽ Ручной режим игры активирован.\n\n"
        "Используйте:\n"
        "/add Фамилия\n"
        "/remove Фамилия\n"
        "/teams"
    )
#=========================
# ADD PLAYER
#=========================
@dp.message(Command("add"))
async def add_player(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/add Фамилия"
        )
        return

    player = parts[1].strip().title()

    if player not in players:
        await message.answer("Такого игрока нет")
        return

    if player in game_state.players_for_game:
        await message.answer(
            f"{player} уже добавлен"
        )
        return

    game_state.players_for_game.append(player)

    await message.answer(
        f"✅ {player} добавлен"
    )
#=========================
# REMOVE PLAYER
#=========================
@dp.message(Command("remove"))
async def remove_player(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/remove Фамилия"
        )
        return

    player = parts[1].strip().title()

    if player not in game_state.players_for_game:
        await message.answer(
            f"{player} не найден"
        )
        return

    game_state.players_for_game.remove(player)

    await message.answer(
        f"❌ {player} удалён"
    )

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

    game_state.current_match_id = None
    game_state.current_red_team = []
    game_state.current_green_team = []
    await message.answer("Игра отменена.")


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
        await message.answer(
    f"Игра активирована на {date}!\n\n"
    f"Используйте /add и /remove для корректировки состава."
)

        await message.answer(
            format_lineup(game_state.players_for_game)
        )   

# =========================
# /TEAMS
# =========================
@dp.message(Command("teams"))
async def teams_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    if not game_state.game_active:
        await message.answer(
            "Сейчас нет активной игры."
        )
        return
    
    if game_state.current_match_id:
        await message.answer(
        "Матч уже создан. Используйте /result."
    )
        return

    if len(game_state.players_for_game) < MIN_PLAYERS:
        await message.answer(
            "Недостаточно игроков."
        )
        return

    # очищаем прошлые команды
    game_state.current_red_team = []
    game_state.current_green_team = []

    # балансировка
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

    game_state.current_red_team = red_team
    game_state.current_green_team = green_team

    # =========================
    # создаём матч в БД
    # =========================

    cursor.execute("""
        INSERT INTO matches (
            status,
            match_date
        )
        VALUES (
            'draft',
            DATE('now')
        )
    """)

    conn.commit()

    match_id = cursor.lastrowid

    game_state.current_match_id = match_id

    # =========================
    # сохраняем составы
    # =========================

    for player in red_team:

        player_id = get_player_id(player)

        cursor.execute("""
            INSERT INTO match_players (
                match_id,
                player_id,
                team
            )
            VALUES (?, ?, ?)
        """, (
            match_id,
            player_id,
            "red"
        ))

    for player in green_team:

        player_id = get_player_id(player)

        cursor.execute("""
            INSERT INTO match_players (
                match_id,
                player_id,
                team
            )
            VALUES (?, ?, ?)
        """, (
            match_id,
            player_id,
            "green"
        ))

    conn.commit()

    # =========================
    # вывод команд
    # =========================

    text = "⚽ Команды сформированы\n\n"

    text += "🔴 Красные:\n"

    for player in red_team:
        text += f"• {player}\n"

    text += "\n🟢 Зеленые:\n"

    for player in green_team:
        text += f"• {player}\n"

    text += f"\n🆔 Матч #{match_id}"

    await message.answer(text)

@dp.message(Command("result"))
async def result_handler(message: Message, state: FSMContext):

    if not game_state.current_match_id:
        await message.answer(
            "Сначала создайте матч через /teams"
        )
        return

    await state.clear()

    await state.update_data(
        match_id=game_state.current_match_id,
        red_team=game_state.current_red_team,
        green_team=game_state.current_green_team,
        goals={},
        goal_history=[]
    )

    team = (
        game_state.current_red_team +
        game_state.current_green_team
    )


    await message.answer(
        "⚽ Назначение голов\n"
        "Нажимайте на игроков."
    )

    await message.answer(
        "Выбирайте игроков:",
        reply_markup=build_goals_kb(team, {})
    )

    await state.set_state(
        GoalInputFSM.goals
    )