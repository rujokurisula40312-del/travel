"""Команда /manager — связаться с менеджером."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.routers.deps import ClientCtx
from src.routers.keyboards import main_menu
from src.services import notifier

log = logging.getLogger(__name__)

router = Router(name="handover")


@router.message(Command("manager"))
async def cmd_manager(message: Message, client: ClientCtx) -> None:
    user = message.from_user
    if not user:
        return
    await notifier.notify_handover(
        message.bot,
        client.config,
        user.id,
        user.username,
        context="Команда /manager",
    )
    await message.answer(
        "Передал менеджеру. Он свяжется с вами в ближайшее рабочее время.",
        reply_markup=main_menu(),
    )
