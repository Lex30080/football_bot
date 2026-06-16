from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot import dp
from app.database.db import cursor, conn
from app.data import players
from app.state.goal_input_fsm import GoalInputFSM
from app.state.game_state import game_state

from app.utils.helpers import get_player_id
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_goals_kb(team, goals):
    kb = InlineKeyboardBuilder()

    for p in team:
        count = goals.get(p, 0)
        kb.button(
            text=f"{p} {'⚽'*count}" if count else p,
            callback_data=f"goal_add:{p}"
        )

    kb.button(text="↩️ undo", callback_data="goal_undo")
    kb.button(text="🏁 finish", callback_data="goal_finish")

    kb.adjust(2)
    return kb.as_markup()


# =========================
# ADD GOAL
# =========================
@dp.callback_query(F.data.startswith("goal_add:"))
async def goal_add(callback: CallbackQuery, state: FSMContext):

    player = callback.data.split(":")[1]
    data = await state.get_data()

    goals = data.get("goals", {})
    history = data.get("goal_history", [])

    goals[player] = goals.get(player, 0) + 1
    history.append(player)

    await state.update_data(goals=goals, goal_history=history)

    team = data["red_team"] + data["green_team"]

    await callback.message.edit_reply_markup(
        reply_markup=build_goals_kb(team, goals)
    )

    await callback.answer()


# =========================
# UNDO
# =========================
@dp.callback_query(F.data == "goal_undo")
async def goal_undo(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    goals = data.get("goals", {})
    history = data.get("goal_history", [])

    if not history:
        await callback.answer("Нет действий")
        return

    last = history.pop()

    goals[last] -= 1
    if goals[last] <= 0:
        del goals[last]

    await state.update_data(goals=goals, goal_history=history)

    team = data["red_team"] + data["green_team"]

    await callback.message.edit_reply_markup(
        reply_markup=build_goals_kb(team, goals)
    )

    await callback.answer()


# =========================
# FINISH MATCH
# =========================
@dp.callback_query(F.data == "goal_finish")
async def goal_finish(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    match_id = data["match_id"]
    red = data["red_team"]
    green = data["green_team"]
    goals = data.get("goals", {})

    red_score = sum(goals.get(p, 0) for p in red)
    green_score = sum(goals.get(p, 0) for p in green)

    if red_score > green_score:
        winner = "red"
    elif green_score > red_score:
        winner = "green"
    else:
        winner = "draw"

    conn.execute("BEGIN")

    cursor.execute("DELETE FROM goals WHERE match_id = ?", (match_id,))

    for player, count in goals.items():
        player_id = get_player_id(player)
        team = "red" if player in red else "green"

        for _ in range(count):
            cursor.execute("""
                INSERT INTO goals (match_id, scorer_id, team)
                VALUES (?, ?, ?)
            """, (match_id, player_id, team))

    cursor.execute("""
        UPDATE matches
        SET red_score=?, green_score=?, winner=?, status='finished'
        WHERE id=?
    """, (red_score, green_score, winner, match_id))

    conn.commit()

    game_state.game_active = False
    game_state.players_for_game = []

    game_state.current_match_id = None
    game_state.current_red_team = []
    game_state.current_green_team = []

    await state.clear()

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        f"✅ Матч завершён\n🔴 {red_score}:{green_score} 🟢\n🏆 {winner}"
    )

    await callback.answer()