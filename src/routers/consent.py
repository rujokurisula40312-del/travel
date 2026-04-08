"""Команда /delete_me — удаление ПД по запросу пользователя."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.domain.states import DeleteMe
from src.routers.deps import ClientCtx
from src.routers.keyboards import delete_me_keyboard, main_menu
from src.usecases import booking as booking_uc

log = logging.getLogger(__name__)

router = Router(name="consent")


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, state: FSMContext) -> None:
    await state.set_state(DeleteMe.waiting_confirmation)
    await message.answer(
        "Вы уверены, что хотите удалить все ваши данные?\n\n"
        "Я удалю ФИО, телефон, email и историю записей из всех туров. "
        "Эта операция <b>необратима</b>.",
        parse_mode="HTML",
        reply_markup=delete_me_keyboard(),
    )


@router.callback_query(F.data == "delete:no", DeleteMe.waiting_confirmation)
async def delete_no(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer("Хорошо, ничего не удаляю.", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "delete:yes", DeleteMe.waiting_confirmation)
async def delete_yes(
    callback: CallbackQuery, state: FSMContext, client: ClientCtx
) -> None:
    user = callback.from_user
    if not user:
        await callback.answer()
        return

    deleted = await booking_uc.delete_user_data(client.spreadsheet_id, user.id)
    await state.clear()

    if deleted:
        text = (
            f"Готово. Удалил ваши данные из {deleted} записей. "
            f"Если захотите снова — просто напишите /start."
        )
    else:
        text = (
            "У меня и так нет ваших данных — записей не найдено. "
            "Если захотите оформить тур — напишите /start."
        )

    if callback.message:
        await callback.message.answer(text, reply_markup=main_menu())
    await callback.answer()
