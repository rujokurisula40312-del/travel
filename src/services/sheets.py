"""Google Sheets — единственный источник данных клиента.

Структура таблицы клиента:
  - `_config` — настройки бота (key/value в первых двух колонках).
  - `_audit`  — журнал событий ФЗ-152.
  - `Шаблон_тура` — шаблон вкладки тура (бот игнорирует).
  - Любая другая вкладка = тур. Сверху метаданные (B1..B15),
    ниже строки лидов (с 18-й строки).

Этот модуль ничего не знает про aiogram и Claude — только про gspread.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Iterable

import gspread
from google.oauth2.service_account import Credentials

from src.config.settings import get_settings
from src.domain.errors import ConfigError, TourNotFound
from src.domain.models import (
    AuditEvent,
    ClientConfig,
    Lead,
    Tour,
)

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Имена служебных листов
SERVICE_SHEET_PREFIXES = ("_",)
TEMPLATE_SHEET_KEYWORDS = ("шаблон", "template")

# Адреса ячеек метаданных тура (см. docs/data-schemas.md)
TOUR_META_CELLS = {
    "tour_id": "B1",
    "country_code": "B2",
    "country_name": "B3",
    "country_aliases": "B4",
    "tour_name": "B5",
    "date_start": "B6",
    "date_end": "B7",
    "price_per_person": "B8",
    "currency": "B9",
    "total_seats": "B10",
    "available_seats": "B11",
    "pdf_file_id": "B12",
    "notion_page_id": "B13",
    "is_active": "B14",
    "short_description": "B15",
}

# Строка с заголовками таблицы лидов и первая строка для данных
LEADS_HEADER_ROW = 17
LEADS_FIRST_DATA_ROW = 18


# ----------------------------------------------------------------------------
# Подключение
# ----------------------------------------------------------------------------


def _build_client() -> gspread.Client:
    settings = get_settings()
    creds = Credentials.from_service_account_info(
        settings.google_service_account, scopes=SCOPES
    )
    return gspread.authorize(creds)


# Глобальный клиент — gspread thread-safe для чтения
_client: gspread.Client | None = None


def get_client() -> gspread.Client:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _is_service_sheet(sheet_name: str) -> bool:
    """True, если лист служебный или шаблонный (бот его игнорирует)."""
    if any(sheet_name.startswith(p) for p in SERVICE_SHEET_PREFIXES):
        return True
    name_lower = sheet_name.lower()
    return any(kw in name_lower for kw in TEMPLATE_SHEET_KEYWORDS)


# ----------------------------------------------------------------------------
# Чтение мастер-таблицы (реестр клиентов)
# ----------------------------------------------------------------------------


async def list_active_clients() -> list[dict]:
    """Возвращает список активных клиентов из мастер-таблицы.

    Каждая запись: {client_id, agency_name, spreadsheet_id}.
    """
    settings = get_settings()
    return await asyncio.to_thread(_list_active_clients_sync, settings.master_config_sheet_id)


def _list_active_clients_sync(master_id: str) -> list[dict]:
    sh = get_client().open_by_key(master_id)
    ws = sh.sheet1
    records = ws.get_all_records()
    return [
        {
            "client_id": r.get("client_id", "").strip(),
            "agency_name": r.get("agency_name", "").strip(),
            "spreadsheet_id": r.get("spreadsheet_id", "").strip(),
        }
        for r in records
        if str(r.get("enabled", "")).strip().upper() in {"TRUE", "1", "YES", "ДА"}
        and r.get("spreadsheet_id")
    ]


# ----------------------------------------------------------------------------
# Чтение конфига клиента (_config)
# ----------------------------------------------------------------------------


async def load_client_config(spreadsheet_id: str) -> ClientConfig:
    return await asyncio.to_thread(_load_client_config_sync, spreadsheet_id)


def _load_client_config_sync(spreadsheet_id: str) -> ClientConfig:
    sh = get_client().open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet("_config")
    except gspread.WorksheetNotFound as exc:
        raise ConfigError(
            f"В таблице {spreadsheet_id} нет листа `_config`"
        ) from exc

    rows = ws.get_all_values()
    cfg: dict[str, str] = {}
    for row in rows:
        if len(row) >= 2 and row[0]:
            cfg[row[0].strip()] = row[1].strip()

    def _required(key: str) -> str:
        value = cfg.get(key, "").strip()
        if not value:
            raise ConfigError(f"В `_config` нет ключа `{key}`")
        return value

    def _int_list(value: str) -> list[int]:
        result: list[int] = []
        for piece in value.split(","):
            piece = piece.strip()
            if piece and piece.lstrip("-").isdigit():
                result.append(int(piece))
        return result

    enabled_raw = cfg.get("enabled", "TRUE").strip().upper()
    return ClientConfig(
        client_id=_required("client_id"),
        agency_name=_required("agency_name"),
        bot_token=_required("bot_token"),
        bot_name=cfg.get("bot_name", "").strip() or "Travel Bot",
        tone=cfg.get("tone", "friendly").strip() or "friendly",  # type: ignore[arg-type]
        manager_telegram_ids=_int_list(cfg.get("manager_telegram_ids", "")),
        owner_telegram_id=int(cfg.get("owner_telegram_id", "0") or 0),
        drive_folder_id=cfg.get("drive_folder_id", "").strip(),
        notion_database_id=cfg.get("notion_database_id", "").strip() or None,
        policy_url=cfg.get("policy_url", "").strip(),
        consent_text_version=cfg.get("consent_text_version", "v1").strip(),
        enabled=enabled_raw in {"TRUE", "1", "YES", "ДА"},
    )


# ----------------------------------------------------------------------------
# Чтение туров (вкладок-туров)
# ----------------------------------------------------------------------------


async def load_tours(spreadsheet_id: str) -> list[Tour]:
    """Возвращает все активные туры из вкладок (кроме служебных)."""
    return await asyncio.to_thread(_load_tours_sync, spreadsheet_id)


def _load_tours_sync(spreadsheet_id: str) -> list[Tour]:
    sh = get_client().open_by_key(spreadsheet_id)
    tours: list[Tour] = []
    for ws in sh.worksheets():
        if _is_service_sheet(ws.title):
            continue
        try:
            tour = _parse_tour_metadata(ws)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Не удалось распарсить вкладку тура %r: %s", ws.title, exc
            )
            continue
        if tour.is_active:
            tours.append(tour)
    return tours


def _parse_tour_metadata(ws: gspread.Worksheet) -> Tour:
    """Парсит метаданные тура из верхней части листа.

    Использует batch_get для одного round-trip к Sheets API вместо 15.
    """
    cells = list(TOUR_META_CELLS.values())
    raw = ws.batch_get(cells)
    values: dict[str, str] = {}
    for key, response in zip(TOUR_META_CELLS.keys(), raw):
        if response and response[0]:
            values[key] = str(response[0][0]).strip()
        else:
            values[key] = ""

    def _opt_date(s: str) -> date | None:
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    def _int(s: str, default: int = 0) -> int:
        try:
            return int(float(s.replace(" ", "").replace(",", "")))
        except (ValueError, TypeError):
            return default

    def _bool(s: str) -> bool:
        return s.upper() in {"TRUE", "1", "YES", "ДА"}

    aliases_raw = values.get("country_aliases", "")
    aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]

    return Tour(
        sheet_name=ws.title,
        tour_id=values.get("tour_id") or ws.title,
        country_code=values.get("country_code", ""),
        country_name=values.get("country_name", ""),
        aliases=aliases,
        tour_name=values.get("tour_name") or ws.title,
        date_start=_opt_date(values.get("date_start", "")),
        date_end=_opt_date(values.get("date_end", "")),
        price_per_person=_int(values.get("price_per_person", "0")),
        currency=values.get("currency") or "RUB",
        total_seats=_int(values.get("total_seats", "0")),
        available_seats=_int(values.get("available_seats", "0")),
        pdf_file_id=values.get("pdf_file_id", ""),
        notion_page_id=values.get("notion_page_id") or None,
        short_description=values.get("short_description", ""),
        is_active=_bool(values.get("is_active", "TRUE")),
    )


# ----------------------------------------------------------------------------
# Запись лида в лист тура
# ----------------------------------------------------------------------------


async def append_lead(spreadsheet_id: str, lead: Lead) -> None:
    """Дописывает лида в конец листа соответствующего тура."""
    await asyncio.to_thread(_append_lead_sync, spreadsheet_id, lead)


def _append_lead_sync(spreadsheet_id: str, lead: Lead) -> None:
    sh = get_client().open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(lead.tour_sheet)
    except gspread.WorksheetNotFound as exc:
        raise TourNotFound(
            f"Не найдена вкладка тура `{lead.tour_sheet}`"
        ) from exc
    ws.append_row(
        lead.to_sheet_row(),
        value_input_option="USER_ENTERED",
        table_range=f"A{LEADS_HEADER_ROW}",
    )


# ----------------------------------------------------------------------------
# Удаление ПД (/delete_me)
# ----------------------------------------------------------------------------


async def delete_lead_by_telegram_id(
    spreadsheet_id: str, telegram_id: int
) -> int:
    """Удаляет все строки с этим telegram_id из всех листов туров.

    Возвращает количество удалённых строк.
    """
    return await asyncio.to_thread(
        _delete_lead_by_telegram_id_sync, spreadsheet_id, telegram_id
    )


def _delete_lead_by_telegram_id_sync(
    spreadsheet_id: str, telegram_id: int
) -> int:
    sh = get_client().open_by_key(spreadsheet_id)
    deleted = 0
    target = str(telegram_id)
    for ws in sh.worksheets():
        if _is_service_sheet(ws.title):
            continue
        # Колонка C — telegram_id (см. data-schemas.md)
        try:
            col_values = ws.col_values(3)
        except Exception:  # noqa: BLE001
            continue
        # Идём с конца, чтобы при удалении не сбить индексы
        rows_to_delete = [
            i + 1
            for i, value in enumerate(col_values)
            if i + 1 >= LEADS_FIRST_DATA_ROW and str(value).strip() == target
        ]
        for row_num in reversed(rows_to_delete):
            try:
                ws.delete_rows(row_num)
                deleted += 1
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Не удалось удалить строку %d в %r: %s",
                    row_num,
                    ws.title,
                    exc,
                )
    return deleted


# ----------------------------------------------------------------------------
# Журнал _audit
# ----------------------------------------------------------------------------


async def append_audit(spreadsheet_id: str, event: AuditEvent) -> None:
    await asyncio.to_thread(_append_audit_sync, spreadsheet_id, event)


def _append_audit_sync(spreadsheet_id: str, event: AuditEvent) -> None:
    sh = get_client().open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet("_audit")
    except gspread.WorksheetNotFound:
        # _audit отсутствует — создаём
        ws = sh.add_worksheet(title="_audit", rows=1000, cols=5)
        ws.append_row(["at", "event", "telegram_id", "tour_sheet", "details"])
    ws.append_row(event.to_sheet_row(), value_input_option="USER_ENTERED")
