"""Хендлеры кнопок главного меню: туры, чек-лист, оплата, менеджер."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from src.domain.errors import TourNotFound
from src.routers.deps import ClientCtx
from src.routers.keyboards import (
    back_to_menu,
    tour_actions,
    tours_list,
)
from src.services import notifier
from src.usecases import program as program_uc
from src.usecases import tours as tours_uc

log = logging.getLogger(__name__)

router = Router(name="menu")


# ----------------------------------------------------------------------------
# Список туров
# ----------------------------------------------------------------------------


@router.callback_query(F.data == "menu:tours")
async def show_tours(callback: CallbackQuery, client: ClientCtx) -> None:
    tours = await tours_uc.get_active_tours(client.spreadsheet_id)
    if not tours:
        if callback.message:
            await callback.message.answer(
                "Сейчас в каталоге нет активных туров. Попробуйте позже или свяжитесь с менеджером.",
                reply_markup=back_to_menu(),
            )
        await callback.answer()
        return

    text = (
        "Вот наши активные туры:\n\n"
        "Нажмите на тур, чтобы посмотреть подробности и получить программу."
    )
    if callback.message:
        await callback.message.answer(text, reply_markup=tours_list(tours))
    await callback.answer()


# ----------------------------------------------------------------------------
# Карточка тура
# ----------------------------------------------------------------------------


@router.callback_query(F.data.startswith("tour:"))
async def show_tour(callback: CallbackQuery, client: ClientCtx) -> None:
    sheet_name = callback.data.split(":", 1)[1] if callback.data else ""
    tour = await tours_uc.find_tour_by_sheet(client.spreadsheet_id, sheet_name)
    if not tour:
        await callback.answer("Тур не найден", show_alert=True)
        return

    seats_line = (
        f"Свободных мест: <b>{tour.available_seats}</b> из {tour.total_seats}"
        if tour.total_seats
        else ""
    )
    parts = [
        f"🌍 <b>{tour.tour_name}</b>",
        f"Страна: {tour.country_name}",
        f"Даты: {tour.display_dates}",
        f"Цена: <b>{tour.display_price}</b> с человека",
    ]
    if seats_line:
        parts.append(seats_line)
    if tour.short_description:
        parts.append("")
        parts.append(tour.short_description)

    if callback.message:
        await callback.message.answer(
            "\n".join(parts),
            parse_mode="HTML",
            reply_markup=tour_actions(tour.sheet_name),
        )
    await callback.answer()


# ----------------------------------------------------------------------------
# Выдача PDF
# ----------------------------------------------------------------------------


@router.callback_query(F.data.startswith("pdf:"))
async def send_pdf(callback: CallbackQuery, client: ClientCtx) -> None:
    sheet_name = callback.data.split(":", 1)[1] if callback.data else ""
    try:
        pdf_bytes, filename = await program_uc.fetch_program_pdf(
            client.spreadsheet_id, sheet_name
        )
    except TourNotFound as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("PDF fetch error: %s", exc)
        await callback.answer("Не удалось загрузить PDF, попробуйте ещё раз.", show_alert=True)
        return

    if callback.message:
        await callback.message.answer_document(
            BufferedInputFile(pdf_bytes, filename=filename),
            caption=f"Программа тура: <b>{sheet_name}</b>",
            parse_mode="HTML",
            reply_markup=tour_actions(sheet_name),
        )
    await callback.answer()


# ----------------------------------------------------------------------------
# Чек-лист и условия оплаты — статичные тексты, потом редактируемые из Sheets
# ----------------------------------------------------------------------------


CHECKLIST_TEXT = (
    "<b>✅ Чек-лист подготовки к поездке</b>\n\n"
    "📄 <b>Документы</b>\n"
    "• Загранпаспорт (срок действия &gt; 6 месяцев на момент возвращения)\n"
    "• Виза, если требуется в страну\n"
    "• Распечатка авиабилетов и брони отеля\n"
    "• Туристическая страховка\n"
    "• Копии документов в отдельной папке/облаке\n\n"
    "💊 <b>Аптечка</b>\n"
    "• Личные лекарства с запасом\n"
    "• Обезболивающее, средства от пищевого отравления\n"
    "• Пластыри, антисептик\n\n"
    "👕 <b>Вещи</b>\n"
    "• Одежда по сезону + одна тёплая вещь\n"
    "• Удобная обувь для прогулок\n"
    "• Адаптер розеток (если нужен)\n"
    "• Зарядки и пауэрбанк\n\n"
    "💳 <b>Деньги и связь</b>\n"
    "• Наличные + карта (узнайте, работает ли в стране)\n"
    "• Местная SIM или роуминг\n"
    "• Контакты посольства РФ в стране назначения"
)

PAYMENT_TEXT = (
    "<b>💳 Условия оплаты и брони</b>\n\n"
    "1. После согласования тура мы фиксируем за вами место.\n"
    "2. Для подтверждения брони — предоплата (обычно 30%).\n"
    "3. Полная оплата — не позднее чем за 14 дней до вылета.\n"
    "4. Оплата по реквизитам, на карту или через эквайринг.\n\n"
    "Точные условия для каждого тура менеджер уточнит индивидуально. "
    "По вопросам — нажмите кнопку «👤 Связаться с менеджером»."
)


@router.callback_query(F.data == "menu:checklist")
async def show_checklist(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(CHECKLIST_TEXT, parse_mode="HTML", reply_markup=back_to_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:payment")
async def show_payment(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer(PAYMENT_TEXT, parse_mode="HTML", reply_markup=back_to_menu())
    await callback.answer()


# ----------------------------------------------------------------------------
# Связь с менеджером (эстафета)
# ----------------------------------------------------------------------------


@router.callback_query(F.data == "menu:manager")
async def request_manager(callback: CallbackQuery, client: ClientCtx) -> None:
    user = callback.from_user
    if not user:
        await callback.answer()
        return

    await notifier.notify_handover(
        callback.bot,
        client.config,
        user.id,
        user.username,
        context="Запрос из главного меню",
    )

    if callback.message:
        await callback.message.answer(
            "Передал ваш контакт менеджеру. Он свяжется с вами в "
            "ближайшее рабочее время. Если хотите ускорить — напишите "
            "ваш вопрос прямо здесь, я его передам.",
            reply_markup=back_to_menu(),
        )
    await callback.answer("Менеджер уведомлён")
