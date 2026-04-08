"""Use-case ИИ-консультанта.

Принимает свободный вопрос туриста, собирает АНОНИМНЫЙ контекст и
обращается в Claude. ПД в Claude не уходят.
"""
from __future__ import annotations

import logging

from src.domain.models import AnonymousContext, ClientConfig, Tour
from src.services import claude
from src.usecases import tours as tours_uc

log = logging.getLogger(__name__)


async def answer_question(
    spreadsheet_id: str,
    config: ClientConfig,
    user_question: str,
    chat_history: list[str] | None = None,
) -> tuple[str, list[Tour]]:
    """Возвращает ответ ИИ + список туров, которые могли совпасть с вопросом.

    chat_history — последние реплики пользователя (без идентификаторов).
    """
    tours = await tours_uc.get_active_tours(spreadsheet_id)

    matched = [t for t in tours if t.matches_country(user_question)]

    tour_summary = None
    if matched:
        first = matched[0]
        tour_summary = (
            f"{first.tour_name} ({first.country_name}, {first.display_dates}, "
            f"{first.display_price} с человека). Доступно мест: "
            f"{first.available_seats}/{first.total_seats}."
        )

    context = AnonymousContext(
        user_question=user_question,
        country_kb_markdown="",  # Notion в фазе 2, пока пусто
        tour_summary=tour_summary,
        chat_history=chat_history or [],
        available_tours=[
            f"{t.tour_name} ({t.country_name})" for t in tours
        ],
    )

    answer_text = await claude.answer(config, context)
    return answer_text, matched
