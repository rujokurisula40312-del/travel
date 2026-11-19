"""
FAQ-бот: отвечает на типовые вопросы туристов кнопками.
Вопросы и ответы — в словаре FAQ ниже. Добавляй свои.

Что настроить:
  BOT_TOKEN — токен от @BotFather
  FAQ       — словарь вопрос → ответ
"""

import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BOT_TOKEN = "ВАШ_ТОКЕН"

FAQ = {
    "🛳 Что такое круиз?": (
        "Круиз — это путешествие на корабле с остановками в разных портах. "
        "Питание, каюта и развлечения включены в стоимость."
    ),
    "💳 Как оплатить тур?": (
        "Принимаем оплату картой (онлайн) или переводом на счёт ИП. "
        "Договор и квитанцию пришлю сразу после оплаты."
    ),
    "📄 Нужна ли виза?": (
        "Зависит от маршрута. Китай и Бразилия — безвиз для россиян. "
        "Египет — виза по прилёту. Уточни страну, скажу точнее."
    ),
    "🌊 Укачивает ли в море?": (
        "Современные лайнеры оснащены стабилизаторами — качка минимальная. "
        "Если склонны к морской болезни, посоветую каюту в середине корабля."
    ),
    "👶 Можно с детьми?": (
        "Да, большинство лайнеров отлично подходят для семей: детские клубы, "
        "бассейны, аниматоры. Уточни возраст ребёнка — подберу маршрут."
    ),
    "📞 Связаться с агентом": (
        "Пиши в любое время! Я на связи с 9:00 до 21:00 по Москве."
    ),
}


def main_kb():
    builder = ReplyKeyboardBuilder()
    for question in FAQ:
        builder.button(text=question)
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


bot = Bot(BOT_TOKEN)
dp  = Dispatcher()


@dp.message(CommandStart())
async def start(msg: types.Message):
    await msg.answer(
        "Привет! Выбери вопрос — отвечу сразу.",
        reply_markup=main_kb(),
    )


@dp.message(F.text.in_(FAQ))
async def answer_faq(msg: types.Message):
    await msg.answer(FAQ[msg.text])


@dp.message()
async def fallback(msg: types.Message):
    await msg.answer(
        "Не нашла такого вопроса. Выбери из меню или напиши напрямую — отвечу лично.",
        reply_markup=main_kb(),
    )


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
