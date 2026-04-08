"""Бизнес-логика поиска и выдачи туров."""
from __future__ import annotations

from src.domain.models import Tour
from src.infra import cache
from src.services import sheets


async def get_active_tours(spreadsheet_id: str) -> list[Tour]:
    """Возвращает активные туры с учётом TTL-кеша."""
    return await cache.tours_cache.get_or_load(
        f"tours:{spreadsheet_id}",
        lambda: sheets.load_tours(spreadsheet_id),
    )


async def find_tour_by_country(
    spreadsheet_id: str, query: str
) -> list[Tour]:
    """Возвращает туры, страна которых упомянута в запросе."""
    tours = await get_active_tours(spreadsheet_id)
    return [t for t in tours if t.matches_country(query)]


async def find_tour_by_sheet(
    spreadsheet_id: str, sheet_name: str
) -> Tour | None:
    """Находит тур по имени вкладки (используется при кнопочной навигации)."""
    tours = await get_active_tours(spreadsheet_id)
    for tour in tours:
        if tour.sheet_name == sheet_name:
            return tour
    return None
