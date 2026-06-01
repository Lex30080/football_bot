from aiogram.filters import Command
from aiogram.types import Message

from app.bot import dp
from app.utils.helpers import is_admin


@dp.message(Command("help"))
async def help_handler(message: Message):

    if is_admin(message.from_user.id):

        text = (
            "🛠 Админ команды\n\n"

            "/game — создать игру вручную\n"
            "/cancel — отменить игру\n"
            "/poll — создать голосование\n"
            "/activate_game — активировать игру из голосования\n"
            "/teams — создать команды\n"
            "/finish — завершить матч\n"
            "/scored — внести голы\n\n"
            "/oldmatch - создать исторический матч\n"
            "/add red фамилия фамилия... - добавить игроков в исторический матч\n\n"
            "/matches — список матчей в базе данных\n"
            "/deletematch id — удалить матч из базы данных\n"
            '/matchdetails id — подробности по матчу\n\n'
            '/removeplayer id — удалить игрока из матча\n'

            
            "👥 Игроки\n"
            "/join Фамилия\n"
            "/leave Фамилия\n"
            "/lineup\n"
            "/stats Фамилия\n"
            "/topscorers"
        )

    else:

        text = (
            "⚽ Команды игрока\n\n"

            "/join Фамилия — записаться\n"
            "/leave Фамилия — выйти\n"
            "/lineup — посмотреть состав\n"
            "/stats Фамилия — статистика игрока\n"
            "/topscorers — лучшие бомбардиры\n\n"

            "Пример:\n"
            "/join Novikov"
        )

    await message.answer(text)