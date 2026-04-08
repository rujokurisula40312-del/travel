"""Use-case записи туриста на тур."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime

from src.domain.errors import InvalidContact
from src.domain.models import (
    AuditEvent,
    ClientConfig,
    Lead,
    LeadDraft,
    Tour,
)
from src.services import sheets

log = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{8,}\d$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


def validate_phone(raw: str) -> str:
    """Возвращает нормализованный телефон или поднимает InvalidContact."""
    cleaned = raw.strip()
    if not PHONE_RE.match(cleaned):
        raise InvalidContact(
            "Не похоже на номер телефона. Попробуйте ещё раз, например: +79161234567"
        )
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 10:
        raise InvalidContact("Слишком короткий номер. Попробуйте ещё раз.")
    if not cleaned.startswith("+"):
        if cleaned.startswith("8") and len(digits) == 11:
            cleaned = "+7" + digits[1:]
        else:
            cleaned = "+" + digits
    return cleaned


def validate_email(raw: str) -> str:
    cleaned = raw.strip().lower()
    if cleaned in {"-", "нет", "пропустить", "skip"}:
        return ""
    if not EMAIL_RE.match(cleaned):
        raise InvalidContact(
            "Не похоже на email. Введите ещё раз или напишите «нет», чтобы пропустить."
        )
    return cleaned


async def book_seat(
    spreadsheet_id: str,
    config: ClientConfig,
    tour: Tour,
    draft: LeadDraft,
) -> Lead:
    """Создаёт лида и записывает в лист тура.

    Бот не занимает места — `is_waitlist` ставится по справочному
    `available_seats`. Реальная бронь происходит после предоплаты,
    которую принимает менеджер.
    """
    if not draft.is_complete():
        raise ValueError("LeadDraft is not complete")

    pax = draft.pax or 1
    is_waitlist = tour.available_seats < pax

    lead = Lead(
        lead_id=str(uuid.uuid4())[:8],
        created_at=datetime.now(),
        tour_sheet=tour.sheet_name,
        telegram_id=draft.telegram_id,
        username=draft.username,
        full_name=draft.full_name or "",
        phone=draft.phone or "",
        email=draft.email,
        pax=pax,
        budget=draft.budget,
        notes=draft.notes,
        consent_at=draft.consent_at,  # type: ignore[arg-type]
        consent_version=config.consent_text_version,
        status="new",
        is_waitlist=is_waitlist,
    )

    await sheets.append_lead(spreadsheet_id, lead)

    await sheets.append_audit(
        spreadsheet_id,
        AuditEvent(
            at=datetime.now(),
            event="waitlist_joined" if is_waitlist else "lead_created",
            telegram_id=lead.telegram_id,
            tour_sheet=lead.tour_sheet,
            details=f"lead_id={lead.lead_id}",
        ),
    )

    return lead


async def delete_user_data(
    spreadsheet_id: str,
    telegram_id: int,
) -> int:
    """Удаляет все записи пользователя из листов туров."""
    deleted = await sheets.delete_lead_by_telegram_id(
        spreadsheet_id, telegram_id
    )
    if deleted:
        await sheets.append_audit(
            spreadsheet_id,
            AuditEvent(
                at=datetime.now(),
                event="lead_deleted",
                telegram_id=telegram_id,
                tour_sheet=None,
                details=f"deleted_rows={deleted}",
            ),
        )
    return deleted
