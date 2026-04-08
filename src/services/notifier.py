"""Уведомления менеджерам в Telegram."""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot

from src.domain.models import ClientConfig, Lead, Tour

log = logging.getLogger(__name__)


async def notify_new_lead(
    bot: Bot,
    config: ClientConfig,
    tour: Tour,
    lead: Lead,
) -> None:
    """Шлёт уведомление о новой записи всем менеджерам клиента."""
    status_label = "📋 Лист ожидания" if lead.is_waitlist else "🟢 Новая запись"

    text = (
        f"<b>{status_label}</b>\n\n"
        f"Тур: <b>{escape(tour.tour_name)}</b>\n"
        f"Вкладка: <code>{escape(tour.sheet_name)}</code>\n"
        f"Даты: {escape(tour.display_dates)}\n"
        f"\n"
        f"Турист: <b>{escape(lead.full_name)}</b>\n"
        f"Телефон: <code>{escape(lead.phone)}</code>\n"
    )
    if lead.email:
        text += f"Email: <code>{escape(lead.email)}</code>\n"
    text += f"Человек: {lead.pax}\n"
    if lead.budget:
        text += f"Бюджет: {lead.budget}\n"
    if lead.notes:
        text += f"Комментарий: {escape(lead.notes)}\n"
    if lead.username:
        text += f"\nTelegram: @{escape(lead.username.lstrip('@'))}\n"
    text += (
        f"\nСогласие ФЗ-152: {lead.consent_at:%Y-%m-%d %H:%M} "
        f"({lead.consent_version})\n"
        f'<a href="tg://user?id={lead.telegram_id}">Открыть чат с туристом</a>'
    )

    for manager_id in config.manager_telegram_ids:
        try:
            await bot.send_message(
                manager_id, text, parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Не смог отправить уведомление менеджеру %s: %s", manager_id, exc)


async def notify_handover(
    bot: Bot,
    config: ClientConfig,
    telegram_id: int,
    username: str | None,
    context: str,
) -> None:
    """Турист просит соединить с менеджером."""
    user_link = (
        f"@{escape(username.lstrip('@'))}" if username else f"id {telegram_id}"
    )
    text = (
        f"<b>🟡 Запрос на связь с менеджером</b>\n\n"
        f"Турист: {user_link}\n"
        f"Контекст: {escape(context) if context else '(не указан)'}\n\n"
        f'<a href="tg://user?id={telegram_id}">Открыть чат</a>'
    )
    for manager_id in config.manager_telegram_ids:
        try:
            await bot.send_message(
                manager_id, text, parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Не смог отправить хэндовер менеджеру %s: %s", manager_id, exc)


async def notify_owner_error(bot: Bot, config: ClientConfig, message: str) -> None:
    """Шлёт алерт об ошибке владельцу бота."""
    if not config.owner_telegram_id:
        return
    try:
        await bot.send_message(
            config.owner_telegram_id,
            f"⚠️ <b>Ошибка бота</b>\n\n<pre>{escape(message[:3500])}</pre>",
            parse_mode="HTML",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Не смог отправить alert владельцу: %s", exc)
