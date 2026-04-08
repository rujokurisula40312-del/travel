"""Настройка логов с маскированием ПД."""
from __future__ import annotations

import logging
import re

_PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


class PIIMaskFilter(logging.Filter):
    """Маскирует телефоны и email в текстах сообщений лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _PHONE_RE.sub("[номер]", record.msg)
            record.msg = _EMAIL_RE.sub("[email]", record.msg)
        return True


def setup(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(PIIMaskFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
