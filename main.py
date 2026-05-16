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

# implementation of the start command
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("⚽ Football bot is running!")


    


async def main():
    print("Bot started")
    await dp.start_polling(bot)

players_for_game =[]

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
    players_for_game = []
    await message.answer("Новая игра началась! нажми /join чтобы записаться")

# implementation of the /join command

@dp.message(Command("join"))
async def join_handler(message: Message):
   if len(players_for_game) >= MAX_PLAYERS:
        await message.answer("Мест нет, 12/12")
        return 
   
   name = message.from_user.first_name
   
   if name not in players_for_game:
       players_for_game.append(name)
       await message.answer(f"{name} присоединился к игре! ({len(players_for_game)}/{MIN_PLAYERS})")
   else:
       await message.answer(f"{name} уже записан на игру.")



asyncio.run(main())