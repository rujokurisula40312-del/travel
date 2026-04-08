"""Сборка клавиатур (inline и reply) для всех экранов бота."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.domain.models import Tour


# ----------------------------------------------------------------------------
# Главное меню (inline)
# ----------------------------------------------------------------------------


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌏 Все туры", callback_data="menu:tours")],
            [InlineKeyboardButton(text="✅ Чек-лист поездки", callback_data="menu:checklist")],
            [InlineKeyboardButton(text="💳 Условия оплаты", callback_data="menu:payment")],
            [InlineKeyboardButton(text="👤 Связаться с менеджером", callback_data="menu:manager")],
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu:main")]
        ]
    )


# ----------------------------------------------------------------------------
# Список туров
# ----------------------------------------------------------------------------


def tours_list(tours: list[Tour]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for tour in tours:
        label = f"🌍 {tour.tour_name}"
        if tour.date_start:
            label += f" · {tour.display_dates}"
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"tour:{tour.sheet_name}")
        ])
    rows.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tour_actions(sheet_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Программа (PDF)", callback_data=f"pdf:{sheet_name}")],
            [InlineKeyboardButton(text="📝 Записаться на тур", callback_data=f"book:{sheet_name}")],
            [InlineKeyboardButton(text="⬅️ К списку туров", callback_data="menu:tours")],
        ]
    )


# ----------------------------------------------------------------------------
# Согласие ФЗ-152
# ----------------------------------------------------------------------------


def consent_keyboard(policy_url: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if policy_url:
        rows.append([InlineKeyboardButton(text="📄 Открыть политику", url=policy_url)])
    rows.append([
        InlineKeyboardButton(text="✅ Согласен", callback_data="consent:yes"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="consent:no"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ----------------------------------------------------------------------------
# Сбор контактов: кнопка «поделиться номером»
# ----------------------------------------------------------------------------


def share_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ----------------------------------------------------------------------------
# Кол-во человек (быстрый выбор)
# ----------------------------------------------------------------------------


def pax_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="pax:1"),
                InlineKeyboardButton(text="2", callback_data="pax:2"),
                InlineKeyboardButton(text="3", callback_data="pax:3"),
                InlineKeyboardButton(text="4+", callback_data="pax:4"),
            ]
        ]
    )


# ----------------------------------------------------------------------------
# Удаление данных
# ----------------------------------------------------------------------------


def delete_me_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data="delete:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="delete:no"),
            ]
        ]
    )
