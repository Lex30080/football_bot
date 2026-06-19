from aiogram.filters import Command
from aiogram.types import Message

from app.bot import dp, bot
from app.utils.settings import set_setting
from app.utils.helpers import is_admin, safe_delete

from aiogram import F
from aiogram.types import Message

from app.bot import dp, bot
from app.utils.settings import get_setting


@dp.message(F.new_chat_members)
async def bot_added_to_group(message: Message):

    for member in message.new_chat_members:

        if member.id != bot.id:
            continue

        # если группа уже настроена — ничего не делаем
        if get_setting("group_id"):
            return

        await message.answer(
            "⚙️ Бот добавлен в группу.\n\n"
            "Для настройки выполните команду:\n"
            "/set_group_id"
        )
        
@dp.message(Command("set_group_id"))
async def set_group_id(message: Message):

    await safe_delete(message)

    if message.chat.type not in ("group", "supergroup"):
        await bot.send_message(
            message.from_user.id,
            "Эта команда работает только в группе."
        )
        return

    if not is_admin(message.from_user.id):
        await bot.send_message(
            message.from_user.id,
            "Только администратор может зарегистрировать группу."
        )
        return

    set_setting("group_id", str(message.chat.id))

    await bot.send_message(
        message.from_user.id,
        f"✅ Группа зарегистрирована.\n\n"
        f"Теперь новости будут отправляться в эту группу.\n\n"
    )

@dp.message(Command("group_info"))
async def group_info(message: Message):

    await safe_delete(message)

    if not is_admin(message.from_user.id):
        return

    group_id = get_setting("group_id")

    if not group_id:
        await bot.send_message(
            message.from_user.id,
            "Группа ещё не настроена."
        )
        return

    await bot.send_message(
        message.from_user.id,
        f"Текущий group_id:\n{group_id}"
    )