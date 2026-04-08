"""FSM-состояния для aiogram.

Используются в `routers/booking.py` для пошагового сбора данных туриста.
"""
from aiogram.fsm.state import State, StatesGroup


class Booking(StatesGroup):
    """Сценарий записи туриста на тур.

    Линейный flow: после подтверждения тура турист идёт через согласие,
    ФИО, телефон, email, кол-во человек.
    """

    waiting_consent = State()
    waiting_name = State()
    waiting_phone = State()
    waiting_email = State()
    waiting_pax = State()
    confirming = State()


class DeleteMe(StatesGroup):
    """Подтверждение удаления данных по /delete_me."""

    waiting_confirmation = State()
