"""Свободный текст → ИИ-консультант + поиск туров."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.routers.deps import ClientCtx
from src.routers.keyboards import tour_actions
from src.usecases import ai_consult

log = logging.getLogger(__name__)

router = Router(name="ai_chat")


@router.message(F.text & ~F.text.startswith("/"))
async def free_text(message: Message, state: FSMContext, client: ClientCtx) -> None:
    # Если внутри FSM (booking) — не перехватываем
    if await state.get_state():
        return

    user_question = (message.text or "").strip()
    if not user_question:
        return

    chat_history: list[str] = []
    data = await state.get_data()
    history = data.get("history") if isinstance(data.get("history"), list) else []
    if history:
        chat_history = list(history)

    try:
        answer, matched_tours = await ai_consult.answer_question(
            client.spreadsheet_id, client.config, user_question, chat_history
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("AI consult error: %s", exc)
        await message.answer(
            "У меня сейчас не получилось ответить. Попробуйте ещё раз или "
            "свяжитесь с менеджером через /menu."
        )
        return

    chat_history.append(user_question)
    if len(chat_history) > 6:
        chat_history = chat_history[-6:]
    await state.update_data(history=chat_history)

    if matched_tours:
        first = matched_tours[0]
        await message.answer(
            answer + f"\n\n📌 Подходящий тур: <b>{first.tour_name}</b>",
            parse_mode="HTML",
            reply_markup=tour_actions(first.sheet_name),
        )
    else:
        await message.answer(answer)
