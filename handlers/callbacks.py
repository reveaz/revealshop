from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import database as db
from handlers.common import ONBOARDING_STEPS, is_admin
from handlers.ui import edit_home, send_home
from handlers.user import CommentForm
from keyboards import (
    main_menu_inline,
    nav_footer_inline,
    onboarding_inline,
    order_detail_inline,
    orders_list_inline,
    settings_inline,
    staff_order_status_full_inline,
    staff_order_status_inline,
    staff_panel_inline,
    admin_orders_inline,
)
from texts import FAQ_PAYMENT, GEOGRAPHY, orders_empty, orders_list_title, screen, staff_panel, stats_text, welcome
from utils import format_order_detail, format_rate_message

router = Router()


@router.callback_query(F.data == "orders:list")
async def cb_orders_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    rows = await db.get_orders_by_user(callback.from_user.id)
    text = orders_empty() if not rows else orders_list_title(len(rows))
    await callback.message.edit_text(text, reply_markup=orders_list_inline(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("order:view:"))
async def cb_order_view(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[-1])
    row = await db.get_order_for_user(order_id, callback.from_user.id)
    if not row:
        await callback.answer("Не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_order_detail(row),
        reply_markup=order_detail_inline(order_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order:comment:"))
async def cb_order_comment(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[-1])
    await state.set_state(CommentForm.text)
    await state.update_data(order_id=order_id)
    await callback.message.answer(f"💬 Комментарий к <b>#{order_id}</b>:")
    await callback.answer()


@router.callback_query(F.data.startswith("order:delete:"))
async def cb_order_delete(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[-1])
    row = await db.get_order_for_user(order_id, callback.from_user.id)
    if not row:
        await callback.answer("Не найден", show_alert=True)
        return
    await db.delete_order(order_id)
    await callback.answer("✅ Заказ удален")
    rows = await db.get_orders_by_user(callback.from_user.id)
    text = orders_empty() if not rows else orders_list_title(len(rows))
    await callback.message.edit_text(text, reply_markup=orders_list_inline(rows))


@router.callback_query(F.data == "info:geo")
async def cb_info_geo(callback: CallbackQuery) -> None:
    await callback.message.answer(GEOGRAPHY, reply_markup=main_menu_inline())
    await callback.answer()


@router.callback_query(F.data == "info:pay")
async def cb_info_pay(callback: CallbackQuery) -> None:
    await callback.message.answer(FAQ_PAYMENT, reply_markup=main_menu_inline())
    await callback.answer()


@router.callback_query(F.data == "settings:notify:toggle")
async def cb_toggle_notify(callback: CallbackQuery) -> None:
    user = await db.get_user(callback.from_user.id)
    current = bool(user["notify_orders"]) if user else True
    await db.set_notify(callback.from_user.id, not current)
    new_on = not current
    try:
        await callback.message.edit_text(
            f"⚙️ <b>Настройки</b>\nУведомления: <b>{'вкл' if new_on else 'выкл'}</b>",
            reply_markup=settings_inline(new_on),
        )
    except Exception:
        pass
    await callback.answer(f"{'Вкл' if new_on else 'Выкл'}")


@router.callback_query(F.data.startswith("onboard:"))
async def cb_onboarding(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if action == "start":
        await callback.message.edit_text(
            ONBOARDING_STEPS[0],
            reply_markup=onboarding_inline(1),
        )
        await callback.answer()
        return

    if action in ("skip", "done"):
        await db.set_onboarding_done(user_id)
        name = callback.from_user.full_name or "друг"
        await callback.message.edit_text("✅ Готово!")
        await callback.message.answer(welcome(name), reply_markup=main_menu_inline())
        await callback.answer()
        return

    step = int(action)
    if step > len(ONBOARDING_STEPS):
        await db.set_onboarding_done(user_id)
        await edit_home(callback, state)
        await callback.answer()
        return

    await callback.message.edit_text(
        ONBOARDING_STEPS[step - 1],
        reply_markup=onboarding_inline(step),
    )
    await callback.answer()


@router.callback_query(F.data == "staff:panel")
async def cb_staff_panel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        staff_panel(),
        reply_markup=staff_panel_inline(),
    )
    await callback.answer()


@router.callback_query(F.data == "staff:orders")
async def cb_staff_orders(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    orders = await db.get_recent_orders(15)
    if not orders:
        await callback.message.edit_text(
            "Заказов нет",
            reply_markup=staff_panel_inline(),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        screen("Заказы", "Выберите заказ:"),
        reply_markup=admin_orders_inline(orders),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("staff:order:"))
async def cb_staff_order(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    row = await db.get_order(order_id)
    if not row:
        await callback.answer("Не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_order_detail(row),
        reply_markup=staff_order_status_inline(order_id, row["status"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("staff:full:"))
async def cb_staff_status_full(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    row = await db.get_order(order_id)
    if not row:
        await callback.answer("Не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_order_detail(row) + "\n<i>выберите статус</i>",
        reply_markup=staff_order_status_full_inline(order_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("staff:st:"))
async def cb_staff_status(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")
    order_id, status_idx = int(parts[2]), int(parts[3])
    if status_idx >= len(db.ORDER_STATUSES):
        await callback.answer("Ошибка", show_alert=True)
        return
    status = db.ORDER_STATUSES[status_idx]
    row = await db.update_order_status(order_id, status)
    if not row:
        await callback.answer("Не найден", show_alert=True)
        return

    user = await db.get_user(row["user_id"])

    # ── Перехват: "Ожидает оплаты" → генерация ссылки Robokassa ──
    if status == "Ожидает оплаты" and user and user["notify_orders"]:
        try:
            from handlers.common import calc_kwargs
            from utils import build_calculation, fmt_money
            from services.robokassa import (
                robokassa_payment_url,
                ReceiptItem,
            )
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            import config

            cost_cny = float(row["cost_cny"]) if row["cost_cny"] else 0.0
            weight = float(row["weight"]) if row["weight"] else 0.0

            kwargs = calc_kwargs()
            kwargs["cny_rate"] = config.CNY_RATE
            kwargs["usd_rate"] = config.USD_RATE
            kwargs["kzt_per_rub"] = config.KZT_PER_RUB
            calc = build_calculation(cost_cny, weight, **kwargs)

            total_rub = calc["total_rub"]

            # ── Фискализация: детализированная номенклатура (ФНС 2026) ──
            cargo = row["cargo_type"] if row["cargo_type"] else "Товар (международная доставка)"
            item_name = f"{cargo}, зак. #{order_id}"

            invoice = robokassa_payment_url(
                inv_id=order_id,
                out_sum=float(total_rub),
                description=f"Заказ #{order_id} — RevealLorder",
                items=[
                    ReceiptItem(name=item_name, quantity=1, sum=float(total_rub)),
                ],
            )

            if invoice:
                await db.record_payment(
                    payment_id=str(order_id),
                    order_id=order_id,
                    amount=float(total_rub),
                    currency="RUB",
                )

                pay_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="💳 Оплатить заказ",
                        url=invoice.payment_url,
                    )],
                ])
                await callback.bot.send_message(
                    row["user_id"],
                    f"📦 <b>Заказ #{order_id}</b> — ожидает оплаты\n\n"
                    f"💰 Сумма: <b>{fmt_money(total_rub)}</b>\n\n"
                    f"Нажмите кнопку ниже для оплаты 👇",
                    reply_markup=pay_kb,
                )
            else:
                # Robokassa не настроена — обычное уведомление
                await callback.bot.send_message(
                    row["user_id"],
                    f"📦 <b>#{order_id}</b> → {status}\n"
                    f"⚠️ Ссылка на оплату будет отправлена отдельно.",
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Robokassa invoice error: %s", e)
            try:
                await callback.bot.send_message(
                    row["user_id"],
                    f"📦 <b>#{order_id}</b> → {status}",
                )
            except Exception:
                pass

    # ── Обычное уведомление для всех остальных статусов ──
    elif user and user["notify_orders"]:
        try:
            await callback.bot.send_message(
                row["user_id"],
                f"📦 <b>#{order_id}</b> → {status}",
            )
        except Exception:
            pass

    await callback.message.edit_text(
        format_order_detail(row) + f"\n<i>{db.STATUS_EMOJI.get(status, '📦')} обновлено</i>",
        reply_markup=staff_order_status_inline(order_id, status),
    )
    await callback.answer(status)


@router.callback_query(F.data.startswith("staff:delete:"))
async def cb_staff_delete(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    await db.delete_order(order_id)
    await callback.answer("✅ Заказ удален")
    orders = await db.get_recent_orders(15)
    if not orders:
        await callback.message.edit_text(
            "Заказов нет",
            reply_markup=staff_panel_inline(),
        )
        return
    await callback.message.edit_text(
        screen("Заказы", "Выберите заказ:"),
        reply_markup=admin_orders_inline(orders),
    )


@router.callback_query(F.data.startswith("staff:track:"))
async def cb_staff_track(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    row = await db.get_order(order_id)
    if not row:
        await callback.answer("Не найден", show_alert=True)
        return
    current_track = row["track_code"] if "track_code" in row.keys() else ""
    from handlers.admin import TrackCodeForm
    await state.set_state(TrackCodeForm.code)
    await state.update_data(track_order_id=order_id)
    hint = f"\n\nТекущий: <code>{current_track}</code>" if current_track else ""
    await callback.message.answer(
        f"📍 Введите трек-код для заказа <b>#{order_id}</b>:{hint}"
    )
    await callback.answer()


@router.callback_query(F.data == "staff:rates")
async def cb_staff_rates(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    from handlers.admin import ManualRateForm
    await state.set_state(ManualRateForm.cny)
    import config
    await callback.message.answer(
        f"Текущие кросс-курсы (вручную):\n"
        f"CNY: {config.CNY_RATE}\n"
        f"USD: {config.USD_RATE}\n\n"
        f"Введите новый курс <b>CNY</b>:"
    )
    await callback.answer()


@router.callback_query(F.data == "staff:stats")
async def cb_staff_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    users = await db.count_users()
    pending = await db.count_pending_orders()
    await callback.message.answer(
        stats_text(users, pending),
        reply_markup=nav_footer_inline("staff:panel"),
    )
    await callback.answer()


@router.callback_query(F.data == "staff:broadcast")
async def cb_staff_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    from handlers.admin import StaffForm

    await state.set_state(StaffForm.broadcast)
    await callback.message.answer("📢 Текст или фото для рассылки:")
    await callback.answer()
