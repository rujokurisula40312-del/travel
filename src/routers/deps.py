"""Зависимости, которые мидлварь прокидывает в каждый хендлер.

Через `data["client"]` каждый хендлер получает {config, spreadsheet_id}
для текущего бота, без необходимости снова читать Sheets.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import ClientConfig


@dataclass(frozen=True)
class ClientCtx:
    """Контекст одного клиента (турагентства), привязан к Bot-инстансу."""

    config: ClientConfig
    spreadsheet_id: str
