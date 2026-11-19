"""
Бот-расписание: клиент выбирает дату и время, запись сохраняется в Google Calendar.
Показывает свободные слоты на ближайшие 2 недели.

Что настроить:
  BOT_TOKEN       — токен от @BotFather
  CALENDAR_ID     — ID календаря (можно найти в настройках Google Calendar)
  CREDENTIALS_FILE— JSON-ключ сервисного аккаунта Google
  SLOTS_PER_DAY   — список доступных времён, например ["10:00", "14:00", "17:00"]
  AVAILABLE_DAYS  — список дней недели (0=пн … 6=вс)
"""

import asyncio, json
from datetime import datetime, timedelta, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from google.oauth2 import service_account
from googleapiclient.discovery import build

BOT_TOKEN        = "ВАШ_ТОКЕН"
CALENDAR_ID      = "ваш@gmail.com"
CREDENTIALS_FILE = "google_creds.json"
SLOTS_PER_DAY    = ["10:00", "13:00", "16:00"]
AVAILABLE_DAYS   = [0, 1, 2, 3, 4]  # пн-пт


def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds)


def free_slots(days_ahead: int = 14) -> list[tuple[date, str]]:
    """Возвращает слоты, не занятые в Google Calendar."""
    svc   = get_calendar_service()
    today = date.today()
    end   = today + timedelta(days=days_ahead)

    events = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=today.isoformat() + "T00:00:00Z",
        timeMax=end.isoformat()   + "T23:59:59Z",
        singleEvents=True,
    ).execute().get("items", [])

    busy = {
        (e["start"].get("dateTime", "")[:10],
         e["start"].get("dateTime", "")[11:16])
        for e in events
    }

    slots = []
    d = today + timedelta(days=1)
    while d <= end:
        if d.weekday() in AVAILABLE_DAYS:
            for t in SLOTS_PER_DAY:
                if (str(d), t) not in busy:
                    slots.append((d, t))
        d += timedelta(days=1)
    return slots[:20]


def create_event(dt_str: str, name: str, phone: str):
    svc   = get_calendar_service()
    start = datetime.fromisoformat(dt_str)
    end   = start + timedelta(hours=1)
    svc.events().insert(
        calendarId=CALENDAR_ID,
        body={
            "summary":     f"Запись: {name}",
            "description": f"Телефон: {phone}",
            "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Moscow"},
            "end":   {"dateTime": end.isoformat(),   "timeZone": "Europe/Moscow"},
        },
    ).execute()


bot = Bot(BOT_TOKEN)
dp  = Dispatcher()


class Book(StatesGroup):
    slot  = State()
    name  = State()
    phone = State()


@dp.message(CommandStart())
async def start(msg: types.Message, state: FSMContext):
    slots = free_slots()
    if not slots:
        await msg.answer("Свободных слотов пока нет. Напиши мне напрямую.")
        return
    await state.update_data(slots=[(str(d), t) for d, t in slots])
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=f"{d.strftime('%d.%m %a')} в {t}",
            callback_data=f"slot:{i}",
        )]
        for i, (d, t) in enumerate(slots)
    ])
    await state.set_state(Book.slot)
    await msg.answer("Выбери удобное время:", reply_markup=kb)


@dp.callback_query(Book.slot, F.data.startswith("slot:"))
async def pick_slot(call: types.CallbackQuery, state: FSMContext):
    idx = int(call.data.split(":")[1])
    data = await state.get_data()
    chosen = data["slots"][idx]
    await state.update_data(chosen=chosen)
    await state.set_state(Book.name)
    await call.message.answer(f"Выбрано: {chosen[0]} в {chosen[1]}\n\nКак тебя зовут?")
    await call.answer()


@dp.message(Book.name)
async def get_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(Book.phone)
    await msg.answer("Телефон для подтверждения:")


@dp.message(Book.phone)
async def get_phone(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    d, t = data["chosen"]
    dt_str = f"{d}T{t}:00+03:00"
    try:
        create_event(dt_str, data["name"], msg.text)
        await msg.answer(
            f"✅ Записала!\n{d} в {t}\nИмя: {data['name']}\n"
            "Жди подтверждения — напишу за день до встречи."
        )
    except Exception as e:
        await msg.answer(f"Ошибка при записи: {e}")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
