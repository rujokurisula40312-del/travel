"""Хендлеры /start, /menu, /help, /reload."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.infra import cache
from src.routers.deps import ClientCtx
from src.routers.keyboards import main_menu

log = logging.getLogger(__name__)

router = Router(name="start")


def _greeting(ctx: ClientCtx) -> str:
    return (
        f"Привет! 👋\n\n"
        f"Я бот турагентства <b>{ctx.config.agency_name}</b>. "
        f"Помогу подобрать тур, отвечу на вопросы и запишу вас на поездку.\n\n"
        f"Выберите, что вас интересует, или просто напишите вопрос — "
        f"например: «Хочу в Китай в апреле»."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, client: ClientCtx) -> None:
    await state.clear()
    await message.answer(_greeting(client), reply_markup=main_menu(), parse_mode="HTML")


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, client: ClientCtx) -> None:
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await message.answer("Отменил. Возвращаемся в главное меню.", reply_markup=main_menu())
    else:
        await message.answer("Нечего отменять. Главное меню:", reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Доступные команды:\n"
        "/start — приветствие и меню\n"
        "/menu — главное меню\n"
        "/cancel — отменить текущий шаг\n"
        "/manager — связаться с менеджером\n"
        "/delete_me — удалить мои данные\n"
        "/help — это сообщение"
    )


@router.message(Command("reload"))
async def cmd_reload(message: Message, client: ClientCtx) -> None:
    """Сброс кешей. Доступно только владельцу бота."""
    if message.from_user and message.from_user.id == client.config.owner_telegram_id:
        await cache.reset_all()
        await message.answer("✅ Кеши сброшены. Свежие данные подтянутся на следующем запросе.")
    else:
        await message.answer("Команда доступна только владельцу бота.")


@router.callback_query(F.data == "menu:main")
async def back_to_main(callback: CallbackQuery, state: FSMContext, client: ClientCtx) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer(_greeting(client), reply_markup=main_menu(), parse_mode="HTML")
    await callback.answer()
