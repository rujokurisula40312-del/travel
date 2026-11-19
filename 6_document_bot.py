"""
Бот для выдачи документов: клиент вводит номер заявки → получает готовый PDF.
Пример: заявление на возврат. Шаблон заполняется автоматически.

Что настроить:
  BOT_TOKEN  — токен от @BotFather
  OWNER_ID   — твой ID (только ты видишь все заявки)
  AGENCY_*   — реквизиты агентства для шаблона
"""

import asyncio, io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BOT_TOKEN = "ВАШ_ТОКЕН"
OWNER_ID  = 123456789

# Реквизиты агентства
AGENCY_NAME   = "ИП Малинкина Анастасия Александровна"
AGENCY_INN    = "695004665880"
AGENCY_OGRN   = "323695200007140"
AGENCY_ADDR   = "170032, г. Тверь, Московское ш., д. 108"
AGENCY_BANK   = "Точка Банк"
AGENCY_RS     = "40802810201500477488"
AGENCY_BIK    = "044525104"

bot = Bot(BOT_TOKEN)
dp  = Dispatcher()


class Refund(StatesGroup):
    order  = State()
    amount = State()
    reason = State()


def make_refund_pdf(order: str, amount: str, reason: str) -> bytes:
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Заголовок
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 80, "ЗАЯВЛЕНИЕ о возврате денежных средств")

    # Данные
    c.setFont("Helvetica", 11)
    lines = [
        f"Прошу Вас произвести возврат в связи с отказом от тура по заявке № {order}.",
        f"Сумма к возврату: {amount} руб.",
        f"Основание: {reason}.",
        "",
        "Получатель: " + AGENCY_NAME,
        "ИНН: " + AGENCY_INN + "   ОГРНИП: " + AGENCY_OGRN,
        "Адрес: " + AGENCY_ADDR,
        "Банк: " + AGENCY_BANK,
        "Р/с: " + AGENCY_RS + "   БИК: " + AGENCY_BIK,
    ]
    y = h - 140
    for line in lines:
        c.drawString(72, y, line)
        y -= 20

    c.setFont("Helvetica", 10)
    from datetime import date
    c.drawString(72, 100, f"Дата: {date.today().strftime('%d.%m.%Y')}")
    c.drawString(72, 80,  "Подпись: ____________________")

    c.save()
    return buf.getvalue()


@dp.message(CommandStart())
async def start(msg: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📄 Заявление на возврат")]],
        resize_keyboard=True,
    )
    await msg.answer("Выбери нужный документ:", reply_markup=kb)


@dp.message(F.text == "📄 Заявление на возврат")
async def refund_start(msg: types.Message, state: FSMContext):
    await state.set_state(Refund.order)
    await msg.answer("Введи номер заявки (например, КМ159069):")


@dp.message(Refund.order)
async def refund_order(msg: types.Message, state: FSMContext):
    await state.update_data(order=msg.text.strip())
    await state.set_state(Refund.amount)
    await msg.answer("Сумма возврата (рублей):")


@dp.message(Refund.amount)
async def refund_amount(msg: types.Message, state: FSMContext):
    await state.update_data(amount=msg.text.strip())
    await state.set_state(Refund.reason)
    await msg.answer("Основание (например: отмена круиза):")


@dp.message(Refund.reason)
async def refund_done(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    pdf = make_refund_pdf(data["order"], data["amount"], msg.text.strip())
    fname = f"Заявление_{data['order']}.pdf"
    await msg.answer_document(
        types.BufferedInputFile(pdf, filename=fname),
        caption=f"Заявка {data['order']}, сумма {data['amount']} руб.",
    )


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
