from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

import re

from app.bot import dp
from app.database.db import conn, cursor
from app.data import players


# =========================
# STATES
# =========================
class HistoricMatchFSM(StatesGroup):
    date = State()
    red_team = State()
    green_team = State()
    goals = State()


# =========================
# UTILS
# =========================
DATE_REGEX = r"^\d{2}\.\d{2}\.\d{4}$"

def is_valid_date(text: str) -> bool:
    return bool(re.match(DATE_REGEX, text.strip()))


def calc_score(goals, red, green):
    r = sum(g["goals"] for g in goals if g["scorer"] in red)
    g = sum(g["goals"] for g in goals if g["scorer"] in green)

    if r > g:
        return r, g, "red"
    if g > r:
        return r, g, "green"
    return r, g, "draw"


# =========================
# KEYBOARDS
# =========================
def build_red_kb(selected):
    kb = InlineKeyboardBuilder()

    for p in players:
        text = f"🔴 {p}" if p in selected else f"⚪ {p}"
        kb.button(text=text, callback_data=f"red:{p}")

    kb.button(text="➡️ Далее", callback_data="red_done")
    kb.adjust(2)
    return kb.as_markup()


def build_green_kb(selected, blocked):
    kb = InlineKeyboardBuilder()

    for p in players:
        if p in blocked:
            continue

        text = f"🟢 {p}" if p in selected else f"⚪ {p}"
        kb.button(text=text, callback_data=f"green:{p}")

    kb.button(text="➡️ Далее", callback_data="green_done")
    kb.adjust(2)
    return kb.as_markup()


# =========================
# START
# =========================
@dp.message(Command("historic"))
async def historic_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📅 Введите дату (ДД.ММ.ГГГГ):")
    await state.set_state(HistoricMatchFSM.date)


# =========================
# DATE
# =========================
@dp.message(HistoricMatchFSM.date)
async def date_step(message: Message, state: FSMContext):

    if not is_valid_date(message.text):
        await message.answer("❌ Формат: ДД.ММ.ГГГГ")
        return

    await state.update_data(
        match_date=message.text.strip(),
        red_team=[],
        green_team=[],
        goals=[]
    )

    await message.answer(
        "🔴 Выберите КРАСНЫХ:",
        reply_markup=build_red_kb([])
    )

    await state.set_state(HistoricMatchFSM.red_team)


# =========================
# RED TOGGLE
# =========================
@dp.callback_query(lambda c: c.data.startswith("red:"))
async def red_pick(callback: CallbackQuery, state: FSMContext):

    player = callback.data.split(":")[1]
    data = await state.get_data()

    red = data.get("red_team", [])

    if player in red:
        red.remove(player)
    else:
        red.append(player)

    await state.update_data(red_team=red)

    await callback.message.edit_reply_markup(
        reply_markup=build_red_kb(red)
    )

    await callback.answer()


@dp.callback_query(lambda c: c.data == "red_done")
async def red_done(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    # ⚠️ важно: убираем старую клавиатуру
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"🔴 Красные: {', '.join(data['red_team'])}\n\n"
    )

    await callback.message.answer(
        "🟢 Выберите зелёных:",
        reply_markup=build_green_kb([], set(data["red_team"]))
    )

    await state.set_state(HistoricMatchFSM.green_team)
    await callback.answer()


# =========================
# GREEN TOGGLE
# =========================
@dp.callback_query(lambda c: c.data.startswith("green:"))
async def green_pick(callback: CallbackQuery, state: FSMContext):

    player = callback.data.split(":")[1]
    data = await state.get_data()

    green = data.get("green_team", [])

    if player in green:
        green.remove(player)
    else:
        green.append(player)

    await state.update_data(green_team=green)

    await callback.message.edit_reply_markup(
        reply_markup=build_green_kb(green, set(data["red_team"]))
    )

    await callback.answer()

def build_goals_kb(team, goals):
    kb = InlineKeyboardBuilder()

    for p in team:
        count = goals.get(p, 0)
        balls = "⚽" * count if count > 0 else ""

        kb.button(
            text=f"{p} {balls}",
            callback_data=f"goal_add:{p}"
        )

    kb.button(text="🧹 Удалить последний", callback_data="goal_undo")
    kb.button(text="🏁 Завершить", callback_data="finish")

    kb.adjust(2)
    return kb.as_markup()

@dp.callback_query(lambda c: c.data == "green_done")
async def green_done(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    green = data["green_team"]

    # убираем клавиатуру выбора зеленых
    await callback.message.edit_reply_markup(reply_markup=None)

    # показываем состав зеленых
    await callback.message.answer(
        f"🟢 Зеленые: {', '.join(green)}"
    )

    team = data["red_team"] + data["green_team"]

    await state.update_data(
        goals={},
        goal_history=[]
    )

    await callback.message.answer(
        "⚽ Назначение голов:\n"
        "1 клик = 1 гол игроку\n"
        "Для исправления используйте кнопку «Удалить последний»"
    )

    await callback.message.answer(
        "Выбирайте игроков:",
        reply_markup=build_goals_kb(team, {})
    )

    await state.set_state(HistoricMatchFSM.goals)

    await callback.answer()


# =========================
# GOALS
# =========================
@dp.callback_query(lambda c: c.data.startswith("goal_add:"))
async def goal_add(callback: CallbackQuery, state: FSMContext):

    player = callback.data.split(":")[1]

    data = await state.get_data()

    goals = data.get("goals", {})
    history = data.get("goal_history", [])

    goals[player] = goals.get(player, 0) + 1

    history.append(player)

    team = data["red_team"] + data["green_team"]

    await state.update_data(
        goals=goals,
        goal_history=history
    )

    await callback.message.edit_reply_markup(
        reply_markup=build_goals_kb(team, goals)
    )

    await callback.answer(f"+1 {player}")

@dp.callback_query(lambda c: c.data == "goal_undo")
async def goal_undo(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    goals = data.get("goals", {})
    history = data.get("goal_history", [])

    if not history:
        await callback.answer("Нет действий для отмены")
        return

    last_player = history.pop()

    goals[last_player] -= 1

    if goals[last_player] <= 0:
        del goals[last_player]

    team = data["red_team"] + data["green_team"]

    await state.update_data(
        goals=goals,
        goal_history=history
    )

    await callback.message.edit_reply_markup(
        reply_markup=build_goals_kb(team, goals)
    )

    await callback.answer(f"Отменён гол: {last_player}")

# =========================
# FINISH
# =========================
@dp.callback_query(lambda c: c.data == "finish")
async def finish(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    goals = data.get("goals", {})

    red = data["red_team"]
    green = data["green_team"]

    red_score = sum(goals.get(p, 0) for p in red)
    green_score = sum(goals.get(p, 0) for p in green)

    if red_score > green_score:
        winner = "red"
    elif green_score > red_score:
        winner = "green"
    else:
        winner = "draw"

    conn.execute("BEGIN")

    cursor.execute("""
        INSERT INTO matches (match_date, red_score, green_score, winner)
        VALUES (?, ?, ?, ?)
    """, (data["match_date"], red_score, green_score, winner))

    match_id = cursor.lastrowid

    # players
    for p in red:
        cursor.execute("""
            INSERT INTO match_players (match_id, player_id, team)
            VALUES (?, ?, 'red')
        """, (match_id, players.index(p) + 1))

    for p in green:
        cursor.execute("""
            INSERT INTO match_players (match_id, player_id, team)
            VALUES (?, ?, 'green')
        """, (match_id, players.index(p) + 1))

    # goals (каждый гол отдельной строкой)
    for player, count in goals.items():
        for _ in range(count):
            cursor.execute("""
                INSERT INTO goals (match_id, scorer_id, team)
                VALUES (?, ?, ?)
            """, (
                match_id,
                players.index(player) + 1,
                "red" if player in red else "green"
            ))

    conn.commit()

    await state.clear()

    await callback.message.delete()
    await callback.message.answer(
        f"✅ Матч сохранён\n\n"
        f"🔴 {red_score} : {green_score} 🟢\n"
        f"🏆 Победитель: {winner}"
    )

    await callback.answer()

# =========================
# Удалить матч из базы данных
# =========================
@dp.message(Command("deletematch"))
async def delete_match(message: Message):

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer("Использование: /deletematch ID")
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    conn.execute("BEGIN")

    cursor.execute(
        "DELETE FROM goals WHERE match_id = ?",
        (match_id,)
    )

    cursor.execute(
        "DELETE FROM match_players WHERE match_id = ?",
        (match_id,)
    )

    cursor.execute(
        "DELETE FROM matches WHERE id = ?",
        (match_id,)
    )

    conn.commit()

    await message.answer(f"🗑 Матч #{match_id} удалён")