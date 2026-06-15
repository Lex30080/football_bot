from aiogram.fsm.state import StatesGroup, State


class GoalInputFSM(StatesGroup):
    goals = State()

