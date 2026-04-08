"""FSM-сценарий записи туриста на тур.

Линейный flow: согласие → ФИО → телефон → email → pax → запись.
"""
from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)

from src.domain.errors import InvalidContact, TourNotFound
from src.domain.models import LeadDraft
from src.domain.states import Booking
from src.routers.deps import ClientCtx
from src.routers.keyboards import (
    consent_keyboard,
    main_menu,
    pax_keyboard,
    share_phone_keyboard,
)
from src.services import notifier, sheets
from src.usecases import booking as booking_uc
from src.usecases import tours as tours_uc

log = logging.getLogger(__name__)

router = Router(name="booking")


# ----------------------------------------------------------------------------
# Старт сценария — нажата кнопка «Записаться»
# ----------------------------------------------------------------------------


@router.callback_query(F.data.startswith("book:"))
async def start_booking(
    callback: CallbackQuery, state: FSMContext, client: ClientCtx
) -> None:
    sheet_name = callback.data.split(":", 1)[1] if callback.data else ""
    tour = await tours_uc.find_tour_by_sheet(client.spreadsheet_id, sheet_name)
    if not tour:
        await callback.answer("Тур не найден", show_alert=True)
        return

    user = callback.from_user
    draft = LeadDraft(
        telegram_id=user.id if user else 0,
        username=user.username if user else None,
        tour_sheet=tour.sheet_name,
    )
    await state.set_data({"draft": draft.__dict__, "tour_sheet": tour.sheet_name})
    await state.set_state(Booking.waiting_consent)

    text = (
        f"Отлично! Записываю на <b>{tour.tour_name}</b> ({tour.display_dates}).\n\n"
        f"Прежде чем продолжить, мне нужно ваше согласие на обработку "
        f"персональных данных. Я попрошу у вас имя, телефон и при желании "
        f"email — мы используем их только для оформления поездки и не "
        f"передаём третьим лицам."
    )
    if callback.message:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=consent_keyboard(client.config.policy_url),
        )
    await callback.answer()


# ----------------------------------------------------------------------------
# Согласие
# ----------------------------------------------------------------------------


@router.callback_query(F.data == "consent:no", Booking.waiting_consent)
async def consent_no(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer(
            "Хорошо, без проблем. Если передумаете — выберите тур ещё раз "
            "и нажмите «Записаться».",
            reply_markup=main_menu(),
        )
    await callback.answer()


@router.callback_query(F.data == "consent:yes", Booking.waiting_consent)
async def consent_yes(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    draft_dict: dict = data.get("draft", {})
    draft_dict["consent_at"] = datetime.now().isoformat()
    await state.update_data(draft=draft_dict)
    await state.set_state(Booking.waiting_name)

    if callback.message:
        await callback.message.answer(
            "Спасибо! 🙏\n\nКак вас зовут? (ФИО полностью)"
        )
    await callback.answer()


# ----------------------------------------------------------------------------
# ФИО
# ----------------------------------------------------------------------------


@router.message(Booking.waiting_name)
async def collect_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 3 or len(name) > 200:
        await message.answer(
            "Похоже, имя ввели не до конца. Напишите ФИО полностью, например: "
            "Иванов Иван Иванович."
        )
        return

    data = await state.get_data()
    draft_dict: dict = data.get("draft", {})
    draft_dict["full_name"] = name
    await state.update_data(draft=draft_dict)
    await state.set_state(Booking.waiting_phone)

    first_name = name.split()[1] if len(name.split()) > 1 else name.split()[0]
    await message.answer(
        f"Приятно познакомиться, {first_name}!\n\n"
        f"Оставьте, пожалуйста, ваш телефон. Можно нажать кнопку ниже, "
        f"чтобы поделиться номером Telegram, или ввести вручную.",
        reply_markup=share_phone_keyboard(),
    )


# ----------------------------------------------------------------------------
# Телефон
# ----------------------------------------------------------------------------


@router.message(Booking.waiting_phone, F.contact)
async def collect_phone_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if not contact or not contact.phone_number:
        await message.answer("Не получилось прочитать номер. Введите вручную.")
        return
    await _save_phone_and_continue(message, state, contact.phone_number)


@router.message(Booking.waiting_phone, F.text)
async def collect_phone_text(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        phone = booking_uc.validate_phone(raw)
    except InvalidContact as exc:
        await message.answer(str(exc))
        return
    await _save_phone_and_continue(message, state, phone)


async def _save_phone_and_continue(
    message: Message, state: FSMContext, raw_phone: str
) -> None:
    try:
        phone = booking_uc.validate_phone(raw_phone)
    except InvalidContact as exc:
        await message.answer(str(exc))
        return

    data = await state.get_data()
    draft_dict: dict = data.get("draft", {})
    draft_dict["phone"] = phone
    await state.update_data(draft=draft_dict)
    await state.set_state(Booking.waiting_email)

    await message.answer(
        f"Записал: <code>{phone}</code>\n\n"
        f"Email для подтверждения брони? Если не хотите оставлять — "
        f"напишите «нет».",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# ----------------------------------------------------------------------------
# Email
# ----------------------------------------------------------------------------


@router.message(Booking.waiting_email)
async def collect_email(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        email = booking_uc.validate_email(raw)
    except InvalidContact as exc:
        await message.answer(str(exc))
        return

    data = await state.get_data()
    draft_dict: dict = data.get("draft", {})
    draft_dict["email"] = email or None
    await state.update_data(draft=draft_dict)
    await state.set_state(Booking.waiting_pax)

    await message.answer("Сколько человек поедет?", reply_markup=pax_keyboard())


# ----------------------------------------------------------------------------
# Кол-во человек → запись
# ----------------------------------------------------------------------------


@router.callback_query(F.data.startswith("pax:"), Booking.waiting_pax)
async def collect_pax(
    callback: CallbackQuery, state: FSMContext, client: ClientCtx
) -> None:
    pax_str = callback.data.split(":", 1)[1] if callback.data else "1"
    try:
        pax = int(pax_str)
    except ValueError:
        pax = 1

    data = await state.get_data()
    draft_dict: dict = data.get("draft", {})
    draft_dict["pax"] = pax
    sheet_name: str = data.get("tour_sheet", "")

    # Восстанавливаем consent_at
    consent_raw = draft_dict.get("consent_at")
    if isinstance(consent_raw, str):
        try:
            draft_dict["consent_at"] = datetime.fromisoformat(consent_raw)
        except ValueError:
            draft_dict["consent_at"] = datetime.now()

    draft = LeadDraft(**{k: v for k, v in draft_dict.items() if k in LeadDraft.__annotations__})

    tour = await tours_uc.find_tour_by_sheet(client.spreadsheet_id, sheet_name)
    if not tour:
        await callback.answer("Тур не найден", show_alert=True)
        await state.clear()
        return

    try:
        lead = await booking_uc.book_seat(
            client.spreadsheet_id, client.config, tour, draft
        )
    except TourNotFound as exc:
        log.error("Booking error: %s", exc)
        if callback.message:
            await callback.message.answer(
                "Извините, произошла ошибка при записи. Передам менеджеру.",
                reply_markup=main_menu(),
            )
        await notifier.notify_owner_error(
            callback.bot, client.config, f"book_seat failed: {exc}"
        )
        await state.clear()
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("Booking unexpected error")
        if callback.message:
            await callback.message.answer(
                "Извините, технический сбой. Передам менеджеру вручную.",
                reply_markup=main_menu(),
            )
        await notifier.notify_owner_error(
            callback.bot, client.config, f"book_seat unexpected: {exc}"
        )
        await state.clear()
        return

    # Уведомление менеджеру
    await notifier.notify_new_lead(callback.bot, client.config, tour, lead)

    # Подтверждение туристу
    if lead.is_waitlist:
        confirmation = (
            f"✅ Записал вашу заявку!\n\n"
            f"⚠️ Обратите внимание: на этот тур формально мест уже нет, "
            f"и вы попадаете в <b>лист ожидания</b>. Если кто-то откажется "
            f"от поездки или мы расширим группу — менеджер сразу с вами "
            f"свяжется.\n\n"
            f"📋 Заявка №<code>{lead.lead_id}</code>\n"
            f"Тур: <b>{tour.tour_name}</b>\n"
            f"Даты: {tour.display_dates}\n"
            f"Человек: {lead.pax}\n"
            f"Статус: <i>лист ожидания</i>"
        )
    else:
        confirmation = (
            f"✅ Готово! Записал вас на тур.\n\n"
            f"📋 Заявка №<code>{lead.lead_id}</code>\n"
            f"Тур: <b>{tour.tour_name}</b>\n"
            f"Даты: {tour.display_dates}\n"
            f"Человек: {lead.pax}\n\n"
            f"Менеджер свяжется с вами в ближайшее рабочее время для "
            f"уточнения деталей и предоплаты. Место в туре фиксируется "
            f"только после внесения предоплаты."
        )

    if callback.message:
        await callback.message.answer(
            confirmation, parse_mode="HTML", reply_markup=main_menu()
        )
    await callback.answer()
    await state.clear()
