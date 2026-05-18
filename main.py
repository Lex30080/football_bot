import asyncio
import os
import random

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from aiogram.filters import Command

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

MIN_PLAYERS = 10
MAX_PLAYERS = 12
game_active = False
players_for_game = []

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


# implementation of the start command
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("⚽ Football bot is running!")


    


async def main():
    print("Bot started")
    await dp.start_polling(bot)



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


# implementation of the players command

@dp.message(Command("players"))
async def players_handler(message: Message):
    text = "Игроки:\n\n"
    shirt = 0
    for player in players:
        shirt += 1
        text += f"{shirt}. {player}\n"
    
    await message.answer(text)


#implementation of the teams command
@dp.message(Command("teams"))
async def teams_handler(message: Message):
    shuffled_players = players.copy()
    random.shuffle(shuffled_players)
    middle = len(shuffled_players) // 2
    red_team = shuffled_players[:middle]
    blue_team = shuffled_players[middle:]
    text = "Команды:\n\n"
    text += "Красная команда:\n"
    for player in red_team:
        text += f"• {player}\n"
    text += "\nСиняя команда:\n"
    for player in blue_team:
        text += f"• {player}\n"

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


# implementation of the /join command
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
    await message.answer("Состав игроков:\n\n" + "\n".join(players_for_game))


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


# implementation of the /leave command
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
    await message.answer_poll(question="Когда играем?", options=parts[1:], allows_multiple_answers=True)

asyncio.run(main())