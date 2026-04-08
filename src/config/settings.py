"""Глобальные настройки процесса (читаются из переменных окружения)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Переменные окружения, общие для всего процесса бота."""

    master_config_sheet_id: str
    google_service_account: dict
    anthropic_api_key: str
    env: str
    log_level: str

    @property
    def is_dev(self) -> bool:
        return self.env.lower() == "dev"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Читает env-переменные. Кешируется на весь процесс."""
    raw_sa = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw_sa:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON не задан. См. .env.example"
        )
    try:
        service_account = json.loads(raw_sa)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON содержит невалидный JSON"
        ) from exc

    master_id = os.environ.get("MASTER_CONFIG_SHEET_ID", "").strip()
    if not master_id:
        raise RuntimeError("MASTER_CONFIG_SHEET_ID не задан. См. .env.example")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан. См. .env.example")

    return Settings(
        master_config_sheet_id=master_id,
        google_service_account=service_account,
        anthropic_api_key=anthropic_key,
        env=os.environ.get("ENV", "dev"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
