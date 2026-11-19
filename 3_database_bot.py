"""
Бот-база данных: хранит записи в SQLite, добавляет и ищет через Telegram.
Пример: база клиентов / финансовых операций / любых данных.

Что настроить:
  BOT_TOKEN  — токен от @BotFather
  OWNER_ID   — твой Telegram user_id (только ты управляешь ботом)
"""

import asyncio, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = "ВАШ_ТОКЕН"
OWNER_ID  = 123456789   # замени на свой ID

DB = "data.db"


def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT,
                phone   TEXT,
                note    TEXT,
                created TEXT DEFAULT (date('now'))
            )
        """)

init_db()

bot = Bot(BOT_TOKEN)
dp  = Dispatcher()


class Add(StatesGroup):
    name  = State()
    phone = State()
    note  = State()


def only_owner(msg: types.Message) -> bool:
    return msg.from_user.id == OWNER_ID


@dp.message(CommandStart())
async def start(msg: types.Message):
    if not only_owner(msg):
        await msg.answer("Нет доступа.")
        return
    await msg.answer(
        "База данных.\n"
        "/add — добавить запись\n"
        "/list — последние 10\n"
        "/search <имя> — поиск"
    )


# ── Добавление ──────────────────────────────────────────────

@dp.message(Command("add"))
async def add_start(msg: types.Message, state: FSMContext):
    if not only_owner(msg): return
    await state.set_state(Add.name)
    await msg.answer("Имя клиента:")

@dp.message(Add.name)
async def add_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(Add.phone)
    await msg.answer("Телефон:")

@dp.message(Add.phone)
async def add_phone(msg: types.Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await state.set_state(Add.note)
    await msg.answer("Заметка (или /skip):")

@dp.message(Add.note)
async def add_note(msg: types.Message, state: FSMContext):
    note = "" if msg.text == "/skip" else msg.text
    data = await state.get_data()
    await state.clear()
    with sqlite3.connect(DB) as conn:
        conn.execute(
            "INSERT INTO records (name, phone, note) VALUES (?,?,?)",
            (data["name"], data["phone"], note),
        )
    await msg.answer(f"✅ Добавлено: {data['name']} {data['phone']}")


# ── Список ───────────────────────────────────────────────────

@dp.message(Command("list"))
async def lst(msg: types.Message):
    if not only_owner(msg): return
    with sqlite3.connect(DB) as conn:
        rows = conn.execute(
            "SELECT id, name, phone, note, created FROM records ORDER BY id DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await msg.answer("База пустая.")
        return
    text = "\n\n".join(
        f"#{r[0]} {r[1]}\n📞 {r[2]}\n📅 {r[4]}" + (f"\n💬 {r[3]}" if r[3] else "")
        for r in rows
    )
    await msg.answer(text)


# ── Поиск ────────────────────────────────────────────────────

@dp.message(Command("search"))
async def search(msg: types.Message):
    if not only_owner(msg): return
    q = msg.text.removeprefix("/search").strip()
    if not q:
        await msg.answer("Используй: /search Иванова")
        return
    with sqlite3.connect(DB) as conn:
        rows = conn.execute(
            "SELECT id, name, phone, note FROM records WHERE name LIKE ?",
            (f"%{q}%",),
        ).fetchall()
    if not rows:
        await msg.answer("Не найдено.")
        return
    text = "\n\n".join(
        f"#{r[0]} {r[1]}\n📞 {r[2]}" + (f"\n💬 {r[3]}" if r[3] else "")
        for r in rows
    )
    await msg.answer(text)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
