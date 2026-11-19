"""
Бот-воронка: выдаёт лид-магнит за подписку на канал.
Участник нажимает /start → бот проверяет подписку → отдаёт файл.

Что настроить:
  CHANNEL_ID   — @username или числовой ID канала
  LEAD_FILE    — путь к PDF/файлу лид-магнита
  BOT_TOKEN    — токен от @BotFather
"""

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

BOT_TOKEN = "ВАШ_ТОКЕН"
CHANNEL_ID = "@ваш_канал"       # или -1001234567890
LEAD_FILE  = "lead_magnet.pdf"  # файл в той же папке

bot = Bot(BOT_TOKEN)
dp  = Dispatcher()


@dp.message(CommandStart())
async def start(msg: types.Message):
    member = await bot.get_chat_member(CHANNEL_ID, msg.from_user.id)
    if member.status in ("member", "administrator", "creator"):
        await msg.answer_document(
            types.FSInputFile(LEAD_FILE),
            caption="Держи! Это твой бонус. Если будут вопросы — пиши.",
        )
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
            types.InlineKeyboardButton(text="Я подписалась ✅", callback_data="check"),
        ]])
        await msg.answer(
            "Чтобы получить материал, подпишись на канал.",
            reply_markup=kb,
        )


@dp.callback_query(lambda c: c.data == "check")
async def check_sub(call: types.CallbackQuery):
    member = await bot.get_chat_member(CHANNEL_ID, call.from_user.id)
    if member.status in ("member", "administrator", "creator"):
        await call.message.answer_document(
            types.FSInputFile(LEAD_FILE),
            caption="Отлично! Держи материал.",
        )
        await call.answer()
    else:
        await call.answer("Подписка пока не найдена. Подпишись и нажми снова.", show_alert=True)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
