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


DB_PATH = "data/football.db"
os.makedirs("data", exist_ok=True)
conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

cursor = conn.cursor()

current_match_id = None # neded for database
current_red_team = []
current_green_team = []

# all availiable players
players = [
    "Айрапетян", 
    "Бабуров",
    "Новиков", 
    "Бирюков", 
    "Тюпаков",
    "Комнатный",
    "Стрижов",
    "Почепец",
    "Колесников",
    "Чечин",
    "Жестеров",
    "Селиванов",
    "Костик",
    "Слинько",
    "Кузнецов",
    "Мурзинов",
    "Букин",
    "Сидоров",
    "Заика", 
    "Спиридонов",
    "Малых",
    "Степанов"
    ]

player_ratings = {
    "Айрапетян": 5,
    "Бабуров": 1,
    "Новиков": 4,
    "Бирюков": 3,
    "Тюпаков": 4,
    "Комнатный": 5,
    "Стрижов": 3,
    "Почепец": 4,
    "Колесников": 5,
    "Чечин": 2,
    "Жестеров": 1,
    "Селиванов": 3,
    "Костик": 1,
    "Слинько": 0,
    "Кузнецов": 0,
    "Мурзинов": 7,
    "Букин": 2,
    "Заика": 2,
    "Сидоров": 1,
    "Спиридонов": 0,
    "Малых": 1, 
    "Степанов": 1
}

telegram_usernames = {
    "atcartsid": "Sidorov",
    "strzhv_d": "Strizhov",
    "Romzes666": "Zaika",
    "aerovit": "Tiupakov",
    "desmatch": "Kostik",
    "r1_sh2": "Slinko",
    "naz_zhe": "Zhesterov",
    "???": "Spiridonov",
    "consciousness007": "Pochepets",
    "mmurz": "Murzinov",
    "????": "Kolesnikov",
    "niksercatc": "Chechin",
    "dmalykhh": "Malykh",
    "Romch_77": "Baburov",
    "one_xtra": "Stepanov",
    "Mikel_Dudikoff": "Bukin",
    "komnatnyiegor": "Komnatniy",
    "??": "Ayrapetian",
    "salivanatc": "Selivanov",
    "?": "Kuznetsov",
    "?????": "Biriukov",
    "Alexgreensleeves": "Novikov"
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

# helper function for database to get active match id 
def get_active_match_id():

    cursor.execute("""
    SELECT id
    FROM matches
    WHERE is_active = 1
    ORDER BY id DESC
    LIMIT 1
    """)

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


# creating tables in the database
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
    winner TEXT,
    status TEXT DEFAULT 'active'       
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

# need this because I need to save match Id in database not in memory
try:
    cursor.execute("""
    ALTER TABLE matches
    ADD COLUMN is_active INTEGER DEFAULT 0
    """)
except:
    pass

# moving player ratings to db
try:
    cursor.execute("""
    ALTER TABLE players
    ADD COLUMN rating INTEGER DEFAULT 0
    """)
except:
    pass

conn.commit()

# helper function for DB to add player
for player in players:
    cursor.execute(
        "INSERT OR IGNORE INTO players (name) VALUES (?)",
        (player,))
conn.commit()

# moving rating to DB
for player_name, rating in player_ratings.items():

    cursor.execute("""
    UPDATE players
    SET rating = ?
    WHERE name = ?
    """, (rating, player_name))

conn.commit()

# helper to get ratings from DB
def get_player_rating(name):

    cursor.execute("""
    SELECT rating
    FROM players
    WHERE name = ?
    """, (name,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0                    


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
        return f"Игроков {len(players_for_game)}/{MAX_PLAYERS}\nМожно бронировать поле\nПродолжаем набор до {MAX_PLAYERS}"
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
    
    global current_red_team
    global current_green_team
    global players_for_game
    global current_match_id

    active_match_id = get_active_match_id()
    if active_match_id is not None:
        await message.answer("Матч уже создан.")
        return

    if not game_active:
        await message.answer("Сейчас нет активной игры.")
        return
    
    if len(players_for_game) < MIN_PLAYERS:
        await message.answer("Недостаточно игроков.")
        return

    
    current_red_team = []
    current_green_team = []

    shuffled_players = players_for_game.copy()
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
    
    current_red_team = red_team.copy()
    current_green_team = green_team.copy()
    
        # деактивируем прошлые матчи
    cursor.execute("""
    UPDATE matches
    SET is_active = 0
    WHERE is_active = 1
    """)

    # создаем новый активный матч
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
    current_match_id = new_match_id

    for player in red_team:
        player_id = get_player_id(player)

        cursor.execute("""
        INSERT INTO match_players (match_id, player_id, team)
        VALUES (?, ?, ?)
        """, (new_match_id, player_id, "red"))

    for player in green_team:
        player_id = get_player_id(player)

        cursor.execute("""
        INSERT INTO match_players (match_id, player_id, team)
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
# I LEFT FOR LATER TO DISCOVER TG IDS OF PLAYERS 

# implementation of the /finish command

@dp.message(Command("finish"))
async def finish_handler(message: Message):
    
    global game_active
    global current_red_team
    global current_green_team

    
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
    
    if match_result[0] != 'active':
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
    game_active = False

    await message.answer(
        f"Матч завершен!\n"
        f"🔴 {red_score} - {green_score} 🟢"
    )

# implementation of the /scored command
@dp.message(Command("scored"))
async def scored_handler(message: Message):
    
    global current_red_team
    global current_green_team
    global players_for_game

    match_id = get_active_match_id()
    if match_id is None:
        await message.answer("Нет активного матча.")
        return
    
    cursor.execute("""
    SELECT COUNT(*)
    FROM goals
    WHERE match_id = ?
    """, (match_id,))

    goals_already_added = cursor.fetchone()[0]

    if goals_already_added > 0:
        await message.answer("Голы для этого матча уже внесены.")
        return
    parts = message.text.split()

    if len(parts) < 3 or len(parts[1:]) % 2 != 0:
        await message.answer(
            "Использование:\n/scored Murzinov 4 Novikov 2"
        )
        return
    goal_data = []
    added_goals = 0

    for i in range(1, len(parts), 2):

        scorer = parts[i]

        try:
            goals_count = int(parts[i + 1])
        except ValueError:
            await message.answer(f"Ошибка в количестве голов у {scorer}")
            return

        player_id = get_player_id(scorer)

        cursor.execute("""
        SELECT team
        FROM match_players
        WHERE match_id = ?
        AND player_id = ?
        """, (match_id, player_id))

        team_result = cursor.fetchone()

        if not team_result:
            await message.answer(f"{scorer} не играл в матче.")
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
        await message.answer(
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

    
    current_red_team = []
    current_green_team = []
    players_for_game = []

    await message.answer(f"⚽ Добавлено голов: {added_goals}")


# implementation of the player stats command
@dp.message(Command("stats"))
async def stats_handler(message: Message):

    parts = message.text.split()

    # проверка аргумента
    if len(parts) < 2:
        await message.answer(
            "Использование:\n/stats Фамилия"
        )
        return

    player_name = parts[1]

    # получаем player_id
    player_id = get_player_id(player_name)

    if player_id is None:
        await message.answer("Игрок не найден.")
        return

    # =========================
    # МАТЧИ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM match_players
    WHERE player_id = ?
    """, (player_id,))

    matches = cursor.fetchone()[0]

    # =========================
    # ГОЛЫ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM goals
    WHERE scorer_id = ?
    """, (player_id,))

    goals = cursor.fetchone()[0]

    # =========================
    # ПОБЕДЫ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM matches m
    JOIN match_players mp
        ON m.id = mp.match_id
    WHERE mp.player_id = ?
    AND (
        (mp.team = 'red' AND m.winner = 'red')
        OR
        (mp.team = 'green' AND m.winner = 'green')
    )
    """, (player_id,))

    wins = cursor.fetchone()[0]

    # =========================
    # ПОРАЖЕНИЯ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM matches m
    JOIN match_players mp
        ON m.id = mp.match_id
    WHERE mp.player_id = ?
    AND (
        (mp.team = 'red' AND m.winner = 'green')
        OR
        (mp.team = 'green' AND m.winner = 'red')
    )
    """, (player_id,))

    losses = cursor.fetchone()[0]

    # =========================
    # НИЧЬИ
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM matches m
    JOIN match_players mp
        ON m.id = mp.match_id
    WHERE mp.player_id = ?
    AND m.winner = 'draw'
    """, (player_id,))

    draws = cursor.fetchone()[0]

    # =========================
    # ОТВЕТ
    # =========================
    text = (
        f"📊 Статистика игрока {player_name}\n\n"
        f"⚽ Матчей: {matches}\n"
        f"🥅 Голов: {goals}\n"
        f"🏆 Побед: {wins}\n"
        f"❌ Поражений: {losses}\n"
        f"🤝 Ничьих: {draws}"
    )

    await message.answer(text)

# implementaion of the /oldmatch command
@dp.message(Command("oldmatch"))
async def newmatch_handler(message: Message):

    # деактивируем прошлые матчи
    cursor.execute("""
    UPDATE matches
    SET is_active = 0
    WHERE is_active = 1
    """)

    # создаем новый матч
    cursor.execute("""
    INSERT INTO matches (
        match_date,
        is_active,
        status
    )
    VALUES (
        DATETIME('now'),
        1,
        'active'
    )
    """)

    conn.commit()

    match_id = cursor.lastrowid

    await message.answer(
        f"Создан матч #{match_id}"
    )

# implementation of the /add command
@dp.message(Command("add"))
async def add_player_handler(message: Message):

    match_id = get_active_match_id()

    if match_id is None:
        await message.answer(
            "Нет активного матча.\nСначала создайте матч."
        )
        return

    parts = message.text.split()

    if len(parts) < 4:
        await message.answer(
            "Использование:\n/add red Murzinov Novikov"
        )
        return

    team = parts[1].lower()

    if team not in ["red", "green"]:
        await message.answer(
            "Команда должна быть red или green"
        )
        return

    players_to_add = parts[2:]

    added_players = []

    for player_name in players_to_add:

        # добавляем игрока в players если его нет
        cursor.execute("""
        INSERT OR IGNORE INTO players (name)
        VALUES (?)
        """, (player_name,))

        conn.commit()

        player_id = get_player_id(player_name)

        # проверяем уже добавлен или нет
        cursor.execute("""
        SELECT *
        FROM match_players
        WHERE match_id = ?
        AND player_id = ?
        """, (match_id, player_id))

        exists = cursor.fetchone()

        if exists:
            continue

        cursor.execute("""
        INSERT INTO match_players (
            match_id,
            player_id,
            team
        )
        VALUES (?, ?, ?)
        """, (match_id, player_id, team))

        added_players.append(player_name)

    conn.commit()

    if added_players:
        await message.answer(
            f"Добавлены в {team}:\n" +
            "\n".join(added_players)
        )
    else:
        await message.answer("Никто не был добавлен.")

# implementation of RATINGS command to see list of ratings
@dp.message(Command("ratings"))
async def ratings_handler(message: Message):

    cursor.execute("""
    SELECT name, rating
    FROM players
    ORDER BY rating DESC
    """)

    players = cursor.fetchall()

    text = "🏆 Рейтинги игроков:\n\n"

    for i, (name, rating) in enumerate(players, start=1):
        text += f"{i}. {name} — {rating}\n"

    await message.answer(text)

# implementation of the SET RATING command

@dp.message(Command("setrating"))
async def setrating_handler(message: Message):

    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "Использование:\n/setrating Murzinov 8"
        )
        return

    player_name = parts[1]

    try:
        new_rating = int(parts[2])
    except ValueError:
        await message.answer("Рейтинг должен быть числом.")
        return

    cursor.execute("""
    UPDATE players
    SET rating = ?
    WHERE name = ?
    """, (new_rating, player_name))

    conn.commit()

    if cursor.rowcount == 0:
        await message.answer("Игрок не найден.")
        return

    await message.answer(
        f"Рейтинг {player_name} изменен на {new_rating}"
    )

# implementation of the /NEWPLAYER command
@dp.message(Command("newplayer"))
async def newplayer_handler(message: Message):

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/newplayer Фамилия"
        )
        return

    player_name = parts[1]

    # проверяем существует ли уже игрок
    cursor.execute("""
    SELECT *
    FROM players
    WHERE name = ?
    """, (player_name,))

    existing_player = cursor.fetchone()

    if existing_player:
        await message.answer(
            f"{player_name} уже существует."
        )
        return

    # создаем игрока
    cursor.execute("""
    INSERT INTO players (name, rating)
    VALUES (?, ?)
    """, (player_name, 0))

    conn.commit()

    # добавляем в список players в памяти
    players.append(player_name)

    await message.answer(
        f"✅ Игрок {player_name} создан."
    )

# implementation of the /REGISTER command
@dp.message(Command("register"))
async def register_handler(message: Message):

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "Использование:\n/register Фамилия"
        )
        return

    player_name = parts[1]

    telegram_id = message.from_user.id

    # проверяем существует ли игрок
    cursor.execute("""
    SELECT id, telegram_id
    FROM players
    WHERE name = ?
    """, (player_name,))

    player = cursor.fetchone()

    if not player:
        await message.answer(
            "Игрок не найден.\nОбратитесь к администратору."
        )
        return

    player_id, existing_telegram_id = player

    # проверяем зарегистрирован ли уже
    if existing_telegram_id is not None:
        await message.answer(
            "Этот игрок уже зарегистрирован."
        )
        return

    # привязываем telegram_id
    cursor.execute("""
    UPDATE players
    SET telegram_id = ?
    WHERE id = ?
    """, (telegram_id, player_id))

    conn.commit()

    await message.answer(
        f"✅ {player_name} успешно зарегистрирован."
    )

async def main():
    try:
        print("Bot started")
        await dp.start_polling(bot)

    finally:
        conn.close()
        print("Database closed")

if __name__ == "__main__":
    asyncio.run(main())