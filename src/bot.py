"""Точка входа Travel Bot Pro.

Запускает один или несколько Telegram-ботов (по одному на клиента из
мастер-таблицы). Каждый бот работает в режиме long polling.

Запуск:
    python -m src.bot
"""
from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.config.settings import get_settings
from src.domain.errors import ConfigError
from src.infra import logging as log_setup
from src.routers import ai_chat, booking, consent, handover, menu, start
from src.routers.deps import ClientCtx
from src.services import sheets

log = logging.getLogger(__name__)


def build_dispatcher(client_ctx: ClientCtx) -> Dispatcher:
    """Создаёт Dispatcher для одного клиента и подключает все роутеры.

    `client_ctx` инжектируется во все хендлеры через `workflow_data`.
    """
    dp = Dispatcher(storage=MemoryStorage())
    dp.workflow_data["client"] = client_ctx

    dp.include_router(start.router)
    dp.include_router(consent.router)
    dp.include_router(handover.router)
    dp.include_router(menu.router)
    dp.include_router(booking.router)
    # ai_chat должен быть последним — он ловит "любой текст без команды"
    dp.include_router(ai_chat.router)

    return dp


async def run_one_bot(client_ctx: ClientCtx) -> None:
    """Запускает long polling одного клиента."""
    bot = Bot(
        token=client_ctx.config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher(client_ctx)
    log.info(
        "Бот %s (%s) стартует. Менеджеры: %s",
        client_ctx.config.bot_name,
        client_ctx.config.client_id,
        client_ctx.config.manager_telegram_ids,
    )
    try:
        await dp.start_polling(bot, handle_signals=False)
    finally:
        await bot.session.close()


async def main() -> None:
    settings = get_settings()
    log_setup.setup(settings.log_level)
    log.info("Travel Bot Pro starting (env=%s)", settings.env)

    clients = await sheets.list_active_clients()
    if not clients:
        log.error(
            "В мастер-таблице %s нет активных клиентов. "
            "Проверьте колонку enabled.",
            settings.master_config_sheet_id,
        )
        sys.exit(1)

    log.info("Найдено активных клиентов: %d", len(clients))

    tasks: list[asyncio.Task[Any]] = []
    for client_record in clients:
        try:
            config = await sheets.load_client_config(client_record["spreadsheet_id"])
        except ConfigError as exc:
            log.error(
                "Не смог загрузить конфиг клиента %s: %s",
                client_record.get("client_id"),
                exc,
            )
            continue
        if not config.enabled:
            log.info("Клиент %s выключен (enabled=FALSE), пропускаем", config.client_id)
            continue
        ctx = ClientCtx(config=config, spreadsheet_id=client_record["spreadsheet_id"])
        tasks.append(asyncio.create_task(run_one_bot(ctx), name=f"bot:{config.client_id}"))

    if not tasks:
        log.error("Ни один бот не запустился. Завершаюсь.")
        sys.exit(1)

    await asyncio.gather(*tasks, return_exceptions=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")
