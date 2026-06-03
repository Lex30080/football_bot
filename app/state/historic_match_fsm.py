from aiogram.fsm.state import State, StatesGroup

class HistoricMatchFSM(StatesGroup):
    date = State()
    red_team = State()
    green_team = State()
    goals = State()
    confirm = State()