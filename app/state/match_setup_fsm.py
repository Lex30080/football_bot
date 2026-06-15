from aiogram.fsm.state import State, StatesGroup

class MatchSetupFSM(StatesGroup):
    date = State()
    red_team = State()
    green_team = State()


