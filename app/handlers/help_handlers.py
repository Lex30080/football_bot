from aiogram.filters import Command
from aiogram.types import Message

from app.bot import dp, bot
from app.utils.helpers import is_admin
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeAllChatAdministrators
)


async def setup_commands():

    await bot.set_my_commands(
        [
            BotCommand(command="help", description="Список команд"),
            BotCommand(command="register", description="Зарегистрироваться"),
        ],
        scope=BotCommandScopeDefault()
    )

    await bot.set_my_commands(
        [
            BotCommand(command="help", description="Список команд"),
        ],
        scope=BotCommandScopeAllChatAdministrators()
    )


@dp.message(Command("help"))
async def help_handler(message: Message):

    if is_admin(message.from_user.id):

        text = (
            "🛠 Админ команды\n\n"

            "/game — создать игру вручную\n"
            "/add фамилия — добавить игрока в игру\n"
            "/remove фамилия — удалить игрока из игры\n"
            "/lineup — смотреть состав\n"
            "/cancel — отменить игру\n\n"

            "/poll — создать голосование\n"
            "/activate_game — активировать игру из голосования\n"
            "/teams — создать команды\n"
            "/result — завершить текущий матч\n\n"

            "/historic — внести прошлый матч\n"
            "/lastmatch — последний матч в базе данных\n"
            "/deletematch id — удалить матч из базы данных\n\n"

            "/set_group_id — зарегистрировать группу для новостей\n"
            "/group_info — получить информацию о группе\n\n"

            "👥 Игроки\n\n"

            "/players — список игроков\n"
            "/ratings — сила игроков\n"
            "/setrating — изменить силу игрока\n"
            "/newplayer — добавить нового игрока\n\n"

            "⚽ Статистика\n\n"

            "/general — общая статистика игр\n"
            "/match id — подробности по матчу\n"
            "/stats Фамилия — статистика игрока\n"
            "/topscorers — лучшие бомбардиры\n"
            "/topmatches — топ по матчам\n\n"

            "🤝 DUO / Связки\n\n"

            "/duo Игрок1 Игрок2 — статистика пары\n"
            "/chemistry Игрок [N] — лучшие партнёры игрока\n"
            "/topduo [N] — лучшие пары по Winrate\n"
            "/topduowins [N] — пары с наибольшим числом побед\n"
            "/topduolosses [N] — пары с наибольшим числом поражений\n"
            "/topduogoals [N] — пары с наибольшим числом забитых голов\n"
            "/topduogoalsagainst [N] — пары с наибольшим числом пропущенных голов\n"
            "/topduodiff [N] — пары с лучшей разницей голов\n"
            "/topduoaverage [N] — среднее число забитых голов за матч\n"
        )

    else:

        text = (
            "⚽ Статистика\n\n"

            "/general — общая статистика игр\n"
            "/match id — подробности по матчу\n"
            "/stats Фамилия — статистика игрока\n"
            "/topscorers — лучшие бомбардиры\n"
            "/topmatches — топ по матчам\n\n"

            "🤝 DUO / Связки\n\n"

            "/duo Игрок1 Игрок2 — статистика пары\n"
            "/chemistry Игрок [N] — лучшие партнёры игрока\n"
            "/topduo [N] — лучшие пары по Winrate\n"
            "/topduoworst [N] — худшие пары по Winrate\n"
            "/topduowins [N] — пары с наибольшим числом побед\n"
            "/topduolosses [N] — пары с наибольшим числом поражений\n"
            "/topduogoals [N] — пары с наибольшим числом забитых голов\n"
            "/topduogoalsagainst [N] — пары с наибольшим числом пропущенных голов\n"
            "/topduodiff [N] — пары с лучшей разницей голов\n"
            "/topduoaverage [N] — среднее число забитых голов за матч\n"
        )

    await message.answer(text)