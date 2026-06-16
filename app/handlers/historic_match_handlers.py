from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot import dp
from app.database.db import cursor, conn
from app.data import players

from app.state.match_setup_fsm import MatchSetupFSM
from app.state.goal_input_fsm import GoalInputFSM

# =========================
# DATE VALIDATION (заглушка под твой regex)
# =========================
import re

DATE_REGEX = r"^(?:(?:0[1-9]|1\d|2[0-8])\.(?:0[1-9]|1[0-2])|(?:29|30)\.(?:0[13-9]|1[0-2])|31\.(?:0[13578]|1[02]))\.(?:202[6-9]|20[3-9]\d|2[1-9]\d{2}|[3-9]\d{3})$"

def is_valid_date(text: str) -> bool:
    return bool(re.match(DATE_REGEX, text.strip()))


# =========================
# RED KB
# =========================
def build_red_kb(selected):
    kb = InlineKeyboardBuilder()

    for p in players:
        kb.button(
            text=f"🔴 {p}" if p in selected else f"⚪ {p}",
            callback_data=f"red:{p}"
        )

    kb.button(text="➡️ Далее", callback_data="red_done")
    kb.adjust(2)
    return kb.as_markup()


# =========================
# START
# =========================
@dp.message(Command("historic"))
async def historic_start(message: Message, state: FSMContext):

    await state.clear()

    # 👉 ВАЖНО: сначала дата
    await state.set_state(MatchSetupFSM.date)

    await message.answer("📅 Введите дату (ДД.ММ.ГГГГ):")


# =========================
# DATE STEP (НОВЫЙ)
# =========================
@dp.message(MatchSetupFSM.date)
async def process_date(message: Message, state: FSMContext):

    date_text = message.text.strip()

    if not is_valid_date(date_text):
        await message.answer("❌ Неверный формат даты")
        return

    await state.update_data(
        match_date=date_text,
        red_team=[],
        green_team=[]
    )

    await state.set_state(MatchSetupFSM.red_team)

    await message.answer(
        "🔴 Выберите КРАСНЫХ:",
        reply_markup=build_red_kb([])
    )


# =========================
# RED PICK
# =========================
@dp.callback_query(F.data.startswith("red:"))
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


# =========================
# RED DONE
# =========================
@dp.callback_query(F.data == "red_done")
async def red_done(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    await callback.message.edit_reply_markup(None)
    await callback.message.delete()

    await state.set_state(MatchSetupFSM.green_team)

    await callback.message.answer(
        f"🔴 Красные: {', '.join(data['red_team'])}"
    )

    await callback.message.answer(
        "🟢 Выберите зелёных:",
        reply_markup=build_green_kb([], set(data["red_team"]))
    )

    await callback.answer()


# =========================
# GREEN KB
# =========================
def build_green_kb(selected, blocked):
    kb = InlineKeyboardBuilder()

    for p in players:
        if p in blocked:
            continue

        kb.button(
            text=f"🟢 {p}" if p in selected else f"⚪ {p}",
            callback_data=f"green:{p}"
        )

    kb.button(text="➡️ Далее", callback_data="green_done")
    kb.adjust(2)
    return kb.as_markup()


# =========================
# GREEN PICK
# =========================
@dp.callback_query(F.data.startswith("green:"))
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


# =========================
# GREEN DONE → CREATE MATCH
# =========================
@dp.callback_query(F.data == "green_done")
async def green_done(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    red = data["red_team"]
    green = data["green_team"]
    match_date = data.get("match_date")

    await callback.message.edit_reply_markup(None)
    await callback.message.delete()

    await callback.message.answer(
        f"🟢 Зеленые: {', '.join(green)}"
    )

    # =========================
    # CREATE MATCH (draft)
    # =========================
    cursor.execute("""
        INSERT INTO matches (status, match_date)
        VALUES ('draft', ?)
    """, (match_date,))
    conn.commit()

    match_id = cursor.lastrowid

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

    conn.commit()

    # =========================
    # SET GOAL FSM DATA
    # =========================
    await state.set_data({
        "match_id": match_id,
        "match_date": match_date,
        "red_team": red,
        "green_team": green,
        "goals": {},
        "goal_history": []
    })

    await state.set_state(GoalInputFSM.goals)

    from app.handlers.goals_input_fsm import build_goals_kb
    team = red + green

    await callback.message.answer(
        "⚽ Ввод голов\n1 клик = +1 гол",
        reply_markup=build_goals_kb(team, {})
    )

    await callback.answer()

#=========================
# DELETE MATCH
#=========================
from aiogram.filters import Command
from aiogram.types import Message

from app.bot import dp
from app.database.db import conn, cursor


@dp.message(Command("deletematch"))
async def delete_match(message: Message):

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer(
            "Использование:\n"
            "/deletematch ID"
        )
        return

    try:
        match_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return

    cursor.execute(
        "SELECT id FROM matches WHERE id = ?",
        (match_id,)
    )

    match_exists = cursor.fetchone()

    if not match_exists:
        await message.answer(
            f"❌ Матч #{match_id} не найден"
        )
        return

    try:
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

        await message.answer(
            f"✅ Матч #{match_id} удалён"
        )

    except Exception as e:

        conn.rollback()

        await message.answer(
            f"❌ Ошибка удаления:\n{e}"
        )