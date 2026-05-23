import asyncio
import os
import random
import sqlite3

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, PollAnswer
from dotenv import load_dotenv
from aiogram.filters import Command

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

conn = sqlite3.connect("football.db")
cursor = conn.cursor()
current_match_id = None # neded for database
current_red_team = []
current_green_team = []

# all availiable players
players = [
    "Ayrapetian", 
    "Baburov",
    "Novikov", 
    "Biriukov", 
    "Tiupakov",
    "Komnatniy",
    "Strizhov",
    "Pochepets",
    "Kolesnikov",
    "Chechin",
    "Zhesterov",
    "Selivanov",
    "Kostik",
    "Slinko",
    "Kuznetsov",
    "Murzinov",
    "Bukin",]

player_ratings = {
    "Ayrapetian": 5,
    "Baburov": 1,
    "Novikov": 4,
    "Biriukov": 3,
    "Tiupakov": 4,
    "Komnatniy": 5,
    "Strizhov": 3,
    "Pochepets": 4,
    "Kolesnikov": 5,
    "Chechin": 2,
    "Zhesterov": 1,
    "Selivanov": 3,
    "Kostik": 1,
    "Slinko": 0,
    "Kuznetsov": 0,
    "Murzinov": 7,
    "Bukin": 2,
    "Zaika": 2,
}

# helper function for database to get player id by name
def get_player_id(name):
    cursor.execute(
        "SELECT id FROM players WHERE name = ?",
        (name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None



# implementation of the database
cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    name TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_date TEXT,
    red_score INTEGER DEFAULT 0,
    green_score INTEGER DEFAULT 0,
    winner TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS match_players (
    match_id INTEGER,
    player_id INTEGER,
    team TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    scorer_id INTEGER,
    team TEXT
)
""")


conn.commit()

# helper function for database to add player
for player in players:
    cursor.execute(
        "INSERT OR IGNORE INTO players (name) VALUES (?)",
        (player,))
conn.commit()

MIN_PLAYERS = 2 # CHANGE LATER TO NORMAL NUMBER
MAX_PLAYERS = 10 # CHANGE LATER TO NORMAL NUMBER

game_active = False
players_for_game = []
poll_votes = {}
poll_options = []

# implementation of the game status
def get_game_status():
    if not game_active:
        return "Нет активной игры."
    elif len(players_for_game) < MIN_PLAYERS:
        return f"Игроков {len(players_for_game)}\nДо игры нужно еще {MIN_PLAYERS - len(players_for_game)} игроков."
    elif len(players_for_game) == MIN_PLAYERS:
        return f"Игрков {len(players_for_game)}/{MAX_PLAYERS}\nМожно бронировать поле\nПродолжаем набор до {MAX_PLAYERS}"
    elif len(players_for_game) < MAX_PLAYERS:
        return f"Игроков {len(players_for_game)}/{MAX_PLAYERS}\nПродолжаем набор до {MAX_PLAYERS}"
    else:
        return f"Игроков {len(players_for_game)}/{MAX_PLAYERS}\nНабор окончен, можно играть!"

# implementation of the lineup formatting
def format_lineup():
    return "Состав игроков:\n\n" + "\n".join(players_for_game)

# implementation of the start command
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("⚽ Football bot is running!")


    


async def main():
    print("Bot started")
    await dp.start_polling(bot)





# implementation of the players command

@dp.message(Command("players"))
async def players_handler(message: Message):
    text = "Игроки:\n\n"
    shirt = 0
    for player in players:
        shirt += 1
        text += f"{shirt}. {player}\n"
    
    await message.answer(text)



# implementation of the /game command

@dp.message(Command("game"))
async def game_handler(message: Message):
    global players_for_game
    global game_active
    if not game_active:
        game_active = True
        players_for_game = []
        await message.answer("Новая игра началась! нажми /join чтобы записаться")
    else:
        await message.answer(f"Набор уже идет! {len(players_for_game)}/{MAX_PLAYERS} игроков записано")    


# implementation of the /join command (NEEDS CORRECTING LATER)
@dp.message(Command("join"))
async def join_handler(message: Message):
   if not game_active:
        await message.answer("❌ Сейчас нет активной игры.\nИспользуйте /game")
        return
   if len(players_for_game) >= MAX_PLAYERS:
        await message.answer("Мест нет, 12/12")
        return 
   
   parts = message.text.split()
   name = parts[1]
   
   if name not in players_for_game:
       players_for_game.append(name)
       status = get_game_status()
       await message.answer(status)
   else:
       await message.answer(f"{name} уже записан на игру.")

# implememntation of the /lineup command
@dp.message(Command("lineup"))
async def lineup_handler(message: Message):
    if not game_active:
        await message.answer("Сейчас нет активной игры.\nИспользуйте /game")
        return
    await message.answer(format_lineup())


# implementaion of the /cancel command
@dp.message(Command("cancel"))
async def cancel_handler(message: Message):
    global game_active
    global players_for_game
    if not game_active:
        await message.answer("Сейчас нет активной игры.")
        return
    game_active = False
    players_for_game = []
    await message.answer("Игра отменена.")


# implementation of the /leave command (NEEDS CORRECTING LATER)
@dp.message(Command("leave"))
async def leave_handler(message: Message):
    global players_for_game
    if not game_active:
        await message.answer("Сейчас нет активной игры.")
        return
    parts = message.text.split()
    name = parts[1]
    if name in players_for_game:
        players_for_game.remove(name)
        status = get_game_status()
        await message.answer(f"{name} покинул игру.\n\n{status}")
    else:
        await message.answer(f"{name} не записан на игру.")

# implementation of the /poll command
@dp.message(Command("poll"))
async def poll_handler(message: Message):
    if len(message.text.split()) < 2:
        await message.answer("Использование: /poll <вариант1> <вариант2> ...")
        return
    parts = message.text.split()
    parts.append("Пас")
    await message.answer_poll(question="Когда играем?", options=parts[1:], is_anonymous=False, allows_multiple_answers=True)
    global poll_options
    global poll_votes
    poll_options = parts[1:]
    poll_votes = {}
    for option in poll_options:
        poll_votes[option] = []
    
@dp.poll_answer()
async def poll_answer_handler(poll_answer: PollAnswer):
    name = poll_answer.user.first_name
    for index, option in enumerate(poll_options):
        if index in poll_answer.option_ids:
            if name not in poll_votes[option]:
                poll_votes[option].append(name)
        else:
            if name in poll_votes[option]:
                poll_votes[option].remove(name)
    # for deubgging purposes
    print(poll_votes)
    
# implementation of the activate_game command
@dp.message(Command("activate_game"))
async def activate_game_handler(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /activate_game <dd.mm>")
        return
    
    date = parts[1]
    global game_active
    global players_for_game
        
        
    if date not in poll_votes:
        await message.answer(f"Проверьте дату")
        return
    players_for_game = poll_votes[date].copy()
    if len(players_for_game) < MIN_PLAYERS:
        await message.answer(f"Недостаточно игроков для начала игры.")
        game_active = False
        return
    else:
        game_active = True
        status = get_game_status()
        await message.answer(f"Игра активирована на {date}!\n\nИспользуйте /join чтобы записаться\n\n")
        await message.answer(status)  
        await message.answer(format_lineup())

# implementation of the /teams command
@dp.message(Command("teams"))
async def teams_handler(message: Message):
    if not game_active:
        await message.answer("Сейчас нет активной игры.")
        return
    
    if len(players_for_game) < MIN_PLAYERS:
        await message.answer("Недостаточно игроков.")
        return

    global current_red_team
    global current_green_team
    global current_match_id

    current_red_team = []
    current_green_team = []

    shuffled_players = players_for_game.copy()
    random.shuffle(shuffled_players)

    sorted_players = sorted(
        shuffled_players,
        key=lambda player: player_ratings.get(player, 0),
        reverse=True
    )

    red_team = []
    green_team = []
    

    for i, player in enumerate(sorted_players):
        if i % 2 == 0:
            red_team.append(player)
        else:
            green_team.append(player)
    
    current_red_team = red_team.copy()
    current_green_team = green_team.copy()
    
    cursor.execute("""
    INSERT INTO matches (match_date)
    VALUES (DATETIME('now'))
    """)

    conn.commit()

    current_match_id = cursor.lastrowid

    for player in red_team:
        player_id = get_player_id(player)

        cursor.execute("""
        INSERT INTO match_players (match_id, player_id, team)
        VALUES (?, ?, ?)
        """, (current_match_id, player_id, "red"))

    for player in green_team:
        player_id = get_player_id(player)

        cursor.execute("""
        INSERT INTO match_players (match_id, player_id, team)
        VALUES (?, ?, ?)
        """, (current_match_id, player_id, "green"))

    conn.commit()

    text = "Команды:\n\n"

    text += "🔴 Красные:\n"
    for player in red_team:
        text += f"• {player}\n"

    text += "\n🟢 Зеленые:\n"
    for player in green_team:
        text += f"• {player}\n"

    await message.answer(text)                             
# I LEFT FOR LATER TO DISCOVER TG IDS OF PLAYERS      
asyncio.run(main())