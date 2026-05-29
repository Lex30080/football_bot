MIN_PLAYERS = 2 # CHANGE LATER TO NORMAL NUMBER
MAX_PLAYERS = 10 # CHANGE LATER TO NORMAL NUMBER

class GameState:
    def __init__(self):
        self.game_active = False
        self.players_for_game = []
        self.current_red_team = []
        self.current_green_team = []
        self.current_match_id = None
        self.poll_options = []
        self.poll_votes = {}

game_state = GameState()