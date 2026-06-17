from aiogram.filters import Command
from aiogram.types import Message
from app.utils.settings import set_setting, get_setting
from app.utils.helpers import is_admin
from app.bot import dp


@dp.message(Command("init_group"))
async def init_group(message: Message):

    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в группе")
        return

    if not is_admin(message.from_user.id):
        await message.answer("Только админ может зарегистрировать группу")
        return

    set_setting("group_id", message.chat.id)

    await message.answer(f"✅ Группа сохранена: {message.chat.id}")