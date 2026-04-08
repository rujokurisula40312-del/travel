"""Use-case выдачи PDF программы тура."""
from __future__ import annotations

from src.domain.errors import TourNotFound
from src.infra import cache
from src.services import drive
from src.usecases import tours as tours_uc


async def fetch_program_pdf(
    spreadsheet_id: str, sheet_name: str
) -> tuple[bytes, str]:
    """Возвращает (содержимое PDF, имя файла) для тура.

    Файл скачивается из Google Drive по `pdf_file_id` из метаданных тура.
    """
    tour = await tours_uc.find_tour_by_sheet(spreadsheet_id, sheet_name)
    if not tour:
        raise TourNotFound(f"Тур `{sheet_name}` не найден")
    if not tour.pdf_file_id:
        raise TourNotFound(
            f"Для тура `{sheet_name}` не указан `pdf_file_id` (ячейка B12)"
        )

    async def loader() -> bytes:
        return await drive.fetch_pdf(tour.pdf_file_id)

    pdf_bytes = await cache.pdf_cache.get_or_load(
        f"pdf:{tour.pdf_file_id}", loader
    )
    filename = f"{tour.tour_id or sheet_name}.pdf"
    return pdf_bytes, filename
