"""
Антиспам-бот: банит спамеров в группе по ключевым словам и паттернам.
Добавь бота в группу и назначь администратором с правом банить.

Что настроить:
  BOT_TOKEN   — токен от @BotFather
  ADMIN_ID    — твой Telegram ID для уведомлений
  SPAM_WORDS  — список стоп-слов (нижний регистр)
"""

import asyncio, re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER

BOT_TOKEN  = "ВАШ_ТОКЕН"
ADMIN_ID   = 123456789

SPAM_WORDS = [
    "заработок", "пассивный доход", "криптовалюта инвестиции",
    "писать в лс", "писать в личку", "набор сотрудников",
    "бесплатное обучение", "1000 в день", "2000 в день",
    "usdt", "binance заработок",
]

SPAM_PATTERNS = [
    r"\+7\s*\d{3}\s*\d{3}[\s-]\d{2}[\s-]\d{2}",  # телефон в тексте
    r"@\w{5,}\s+набор",                             # @юзер + слово "набор"
]

bot = Bot(BOT_TOKEN)
dp  = Dispatcher()


def is_spam(text: str) -> str | None:
    """Возвращает причину если спам, иначе None."""
    t = text.lower()
    for word in SPAM_WORDS:
        if word in t:
            return f"стоп-слово: {word}"
    for pat in SPAM_PATTERNS:
        if re.search(pat, t, re.I):
            return f"паттерн: {pat}"
    return None


@dp.message(F.text)
async def check_message(msg: types.Message):
    if msg.chat.type not in ("group", "supergroup"):
        return
    if msg.from_user.is_bot:
        return

    reason = is_spam(msg.text or "")
    if not reason:
        return

    try:
        await msg.delete()
        await msg.chat.ban(msg.from_user.id)
    except Exception:
        pass

    await bot.send_message(
        ADMIN_ID,
        f"🚫 Забанила спамера в «{msg.chat.title}»\n"
        f"Кто: @{msg.from_user.username or msg.from_user.id} (id {msg.from_user.id})\n"
        f"Причина: {reason}\n"
        f"Статус: удалено=True, забанен=True\n\n"
        f"Сообщение:\n{msg.text[:300]}",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text="Разбанить",
                callback_data=f"unban:{msg.chat.id}:{msg.from_user.id}",
            )
        ]]),
    )


@dp.callback_query(F.data.startswith("unban:"))
async def unban(call: types.CallbackQuery):
    _, chat_id, user_id = call.data.split(":")
    await bot.unban_chat_member(int(chat_id), int(user_id))
    await call.message.edit_text(call.message.text + "\n\n✅ Разбанен")
    await call.answer("Разбанен")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
