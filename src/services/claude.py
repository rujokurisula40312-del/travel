"""Anthropic Claude — ИИ-консультант.

КРИТИЧНО: эта функция принимает только AnonymousContext. ПД сюда не
попадают by design — это техническое выполнение требований ФЗ-152.
"""
from __future__ import annotations

import logging
import re

from anthropic import AsyncAnthropic

from src.config.settings import get_settings
from src.domain.models import AnonymousContext, ClientConfig

log = logging.getLogger(__name__)

# Защитная сетка: маскируем телефоны и email на случай, если что-то
# случайно попало в текст вопроса.
_PHONE_RE = re.compile(r"(\+?\d[\d\s\-\(\)]{8,}\d)")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

MODEL_NAME = "claude-sonnet-4-5"
MAX_TOKENS = 1024


def _scrub(text: str) -> str:
    text = _PHONE_RE.sub("[номер]", text)
    text = _EMAIL_RE.sub("[email]", text)
    return text


_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def build_system_prompt(client: ClientConfig, available_tours: list[str]) -> str:
    """Строит системный промпт под конкретное турагентство."""
    tone_guide = (
        "Общайся тепло, простыми словами, на «вы». Можно использовать смайлики умеренно."
        if client.tone == "friendly"
        else "Общайся вежливо и сдержанно, на «вы». Без смайликов."
    )

    tours_list = "\n".join(f"- {t}" for t in available_tours) if available_tours else "(пока нет активных туров)"

    return f"""Ты — ИИ-консультант турагентства «{client.agency_name}». Тебя зовут {client.bot_name}.

ТОН: {tone_guide}

ТЫ МОЖЕШЬ:
- Рассказывать про туры из списка ниже.
- Отвечать на вопросы про визы, климат, что брать с собой, безопасность, питание, связь.
- Помогать определиться с направлением.
- Признавать, что чего-то не знаешь, и предлагать связаться с менеджером.

ТЫ НЕ МОЖЕШЬ И НЕ ДОЛЖНА:
- Называть конкретные цены, точные даты или количество мест из головы — для этого есть кнопка «Программа».
- Обещать ничего, что не указано в базе знаний.
- Отвечать на вопросы, не связанные с туризмом и поездками. На любой оффтоп — короткий вежливый отказ и предложение вернуться к турам.
- Запрашивать у пользователя ФИО, телефон или email — это делает другой блок бота.
- Упоминать, что ты ИИ, нейросеть, GPT или Claude — представляешься помощником турагентства.

АКТИВНЫЕ НАПРАВЛЕНИЯ:
{tours_list}

Отвечай кратко (2–4 предложения), по делу. В конце ответа можно мягко предложить программу тура или связаться с менеджером, если это уместно.
"""


async def answer(
    config: ClientConfig,
    context: AnonymousContext,
) -> str:
    """Спрашивает Claude и возвращает ответ туристу.

    Все входы — анонимны (нет ФИО, телефона, email, telegram_id).
    """
    settings = get_settings()
    client = get_client()

    system = build_system_prompt(config, context.available_tours)
    if context.country_kb_markdown:
        system += "\n\nКОНТЕКСТ ПО СТРАНЕ (из базы знаний агентства):\n"
        system += context.country_kb_markdown

    if context.tour_summary:
        system += f"\n\nПОДОБРАННЫЙ ТУР: {context.tour_summary}"

    messages = []
    for turn in context.chat_history[-6:]:
        messages.append({"role": "user", "content": _scrub(turn)})
    messages.append({"role": "user", "content": _scrub(context.user_question)})

    try:
        response = await client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Claude API error: %s", exc)
        return (
            "Кажется, у меня сейчас сложности с ответом. Передам вопрос "
            "менеджеру — он скоро с вами свяжется. Можете нажать кнопку "
            "«👤 Менеджер»."
        )

    parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip() or (
        "Хм, не уверен, что ответил по делу. Попробуйте уточнить вопрос или "
        "позовите менеджера через кнопку «👤 Менеджер»."
    )
