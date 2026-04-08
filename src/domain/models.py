"""Доменные модели Travel Bot Pro.

Здесь живут чистые dataclass'ы — без зависимостей от Telegram, gspread,
Anthropic и прочей инфраструктуры. Это позволяет тестировать бизнес-логику
изолированно и переиспользовать модели в разных слоях.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


# ----------------------------------------------------------------------------
# Конфиг клиента (читается из листа `_config` таблицы клиента)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class ClientConfig:
    """Настройки одного клиента (турагентства).

    Читается из листа `_config` таблицы клиента при старте бота и периодически
    обновляется по TTL.
    """

    client_id: str
    agency_name: str
    bot_token: str
    bot_name: str
    tone: Literal["friendly", "formal"]
    manager_telegram_ids: list[int]
    owner_telegram_id: int
    drive_folder_id: str
    notion_database_id: str | None
    policy_url: str
    consent_text_version: str
    enabled: bool


# ----------------------------------------------------------------------------
# Тур (читается из вкладки тура в таблице клиента)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Tour:
    """Метаданные тура из верхней части листа тура.

    `sheet_name` — имя вкладки в Sheets, оно же отображаемое название тура
    для туриста.
    """

    sheet_name: str
    tour_id: str
    country_code: str
    country_name: str
    aliases: list[str]
    tour_name: str
    date_start: date | None
    date_end: date | None
    price_per_person: int
    currency: str
    total_seats: int
    available_seats: int
    pdf_file_id: str
    notion_page_id: str | None
    short_description: str
    is_active: bool

    @property
    def display_dates(self) -> str:
        """Формат: «15–25 апреля 2025»."""
        if not self.date_start or not self.date_end:
            return "даты уточняются"
        months_ru = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря",
        ]
        if self.date_start.month == self.date_end.month:
            return (
                f"{self.date_start.day}–{self.date_end.day} "
                f"{months_ru[self.date_start.month - 1]} {self.date_end.year}"
            )
        return (
            f"{self.date_start.day} {months_ru[self.date_start.month - 1]} – "
            f"{self.date_end.day} {months_ru[self.date_end.month - 1]} "
            f"{self.date_end.year}"
        )

    @property
    def display_price(self) -> str:
        """Формат: «185 000 ₽» или «1 200 USD»."""
        symbols = {"RUB": "₽", "USD": "$", "EUR": "€"}
        formatted_price = f"{self.price_per_person:,}".replace(",", " ")
        symbol = symbols.get(self.currency, self.currency)
        if symbol in {"₽"}:
            return f"{formatted_price} {symbol}"
        return f"{symbol} {formatted_price}"

    def matches_country(self, query: str) -> bool:
        """Проверяет, упоминает ли запрос страну этого тура."""
        query_lower = query.lower()
        if self.country_name.lower() in query_lower:
            return True
        for alias in self.aliases:
            if alias.lower() and alias.lower() in query_lower:
                return True
        return False


# ----------------------------------------------------------------------------
# Лид (запись туриста)
# ----------------------------------------------------------------------------


@dataclass
class LeadDraft:
    """Заполняемый во время FSM-сценария лид.

    Записывается в Sheets только после полного заполнения и согласия на ПД.
    """

    telegram_id: int
    username: str | None
    tour_sheet: str  # имя вкладки в Sheets, куда писать
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    pax: int | None = None
    budget: int | None = None
    notes: str | None = None
    consent_at: datetime | None = None

    def is_complete(self) -> bool:
        """Готов ли драфт к записи в Sheets?"""
        return all(
            (
                self.full_name,
                self.phone,
                self.pax is not None,
                self.consent_at is not None,
            )
        )


@dataclass(frozen=True)
class Lead:
    """Финальный лид, готовый к записи в лист тура."""

    lead_id: str
    created_at: datetime
    tour_sheet: str
    telegram_id: int
    username: str | None
    full_name: str
    phone: str
    email: str | None
    pax: int
    budget: int | None
    notes: str | None
    consent_at: datetime
    consent_version: str
    status: Literal["new", "contacted", "paid", "cancelled"]
    is_waitlist: bool

    def to_sheet_row(self) -> list:
        """Преобразует лида в строку для append_row в Sheets."""
        return [
            self.lead_id,
            self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            self.telegram_id,
            self.username or "",
            self.full_name,
            self.phone,
            self.email or "",
            self.pax,
            self.budget or "",
            self.notes or "",
            self.consent_at.strftime("%Y-%m-%d %H:%M:%S"),
            self.consent_version,
            self.status,
            "TRUE" if self.is_waitlist else "FALSE",
        ]


# ----------------------------------------------------------------------------
# Контекст для Claude (БЕЗ ПД!)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class AnonymousContext:
    """Всё, что МОЖНО отправить в Claude API.

    ПД (ФИО, телефон, email, telegram_id) сюда не кладутся by design — это
    защищает от случайной утечки на сторону Anthropic. Если в коде кто-то
    попытается отправить в Claude что-то кроме AnonymousContext, type checker
    подсветит ошибку.
    """

    user_question: str
    country_kb_markdown: str = ""
    tour_summary: str | None = None
    chat_history: list[str] = field(default_factory=list)
    available_tours: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------
# Запись в журнале _audit
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditEvent:
    """Событие в журнале аудита (без ПД)."""

    at: datetime
    event: Literal[
        "consent_given",
        "lead_created",
        "lead_deleted",
        "waitlist_joined",
        "manager_handover",
        "error",
    ]
    telegram_id: int | None
    tour_sheet: str | None
    details: str

    def to_sheet_row(self) -> list:
        return [
            self.at.strftime("%Y-%m-%d %H:%M:%S"),
            self.event,
            self.telegram_id or "",
            self.tour_sheet or "",
            self.details,
        ]
