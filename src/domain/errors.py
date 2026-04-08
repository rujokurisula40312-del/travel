"""Доменные исключения."""


class DomainError(Exception):
    """Базовый класс для всех доменных ошибок."""


class TourNotFound(DomainError):
    """Тур или страна не найдены в базе клиента."""


class ConfigError(DomainError):
    """Конфиг клиента невалиден или отсутствует."""


class InvalidContact(DomainError):
    """Не удалось распарсить телефон или email."""


class ConsentRequired(DomainError):
    """Действие требует согласия на обработку ПД, а оно не получено."""
