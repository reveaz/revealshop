from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import database as db
from handlers.common import is_admin
from texts import admin_header, staff_panel
from keyboards import main_menu_inline, staff_panel_inline

router = Router()


class StaffForm(StatesGroup):
    broadcast = State()


class ManualRateForm(StatesGroup):
    cny = State()
    usd = State()


class TrackCodeForm(StatesGroup):
    code = State()


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    role = "админ" if is_admin(uid) else "пользователь"
    await message.answer(f"ID <code>{uid}</code> · {role}")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    users = await db.count_users()
    pending = await db.count_pending_orders()
    await message.answer(
        admin_header(users, pending),
        reply_markup=staff_panel_inline(),
@router.message(Command("staff"))
async def cmd_staff(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("⛔ Нет доступа.")
        return
    await state.clear()
    await message.answer(staff_panel(), reply_markup=staff_panel_inline())


@router.message(TrackCodeForm.code)
async def staff_track_code_input(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await state.clear()
        return

    data = await state.get_data()
    order_id = data.get("track_order_id")
    if not order_id:
        await state.clear()
        await message.answer("Ошибка, попробуйте снова.")
        return

    track_code = (message.text or "").strip()
    if not track_code or len(track_code) < 3:
        await message.answer("❌ Трек-код слишком короткий. Введите ещё раз:")
        return

    ok = await db.set_order_track_code(order_id, track_code)
    if not ok:
        await state.clear()
        await message.answer("❌ Заказ не найден.")
        return

    # Notify the user about the tracking code
    order = await db.get_order(order_id)
    if order:
        user = await db.get_user(order["user_id"])
        if user and user["notify_orders"]:
            try:
                await message.bot.send_message(
                    order["user_id"],
                    f"📍 <b>#{order_id}</b> — трек-код присвоен\n\n"
                    f"🔎 <code>{track_code}</code>\n\n"
                    f"📌 Статус: <b>{order['status']}</b>",
                )
            except Exception:
                pass

    await state.clear()
    await message.answer(
        f"✅ Трек-код <code>{track_code}</code> сохранён для заказа <b>#{order_id}</b>\n"
        f"🔍 Запускаю проверку статуса…",
        reply_markup=main_menu_inline(),
    )

    # Trigger immediate tracking check in background
    import asyncio
    from services.auto_track import check_single_order

    async def _do_check():
        new_status = await check_single_order(message.bot, order_id)
        if new_status:
            await message.answer(
                f"🔄 Статус заказа <b>#{order_id}</b> обновлён → <b>{new_status}</b>"
            )
        else:
            await message.answer(
                f"ℹ️ Заказ <b>#{order_id}</b>: статус не изменился "
                f"(будет проверяться автоматически каждые 30 мин)"
            )

    asyncio.create_task(_do_check())


@router.message(ManualRateForm.cny)
async def admin_rate_cny(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await state.clear()
        return
    from utils import parse_number
    val = parse_number(message.text or "")
    if not val:
        await message.answer("Число, напр. 11.5")
        return
    await state.update_data(new_cny=val)
    await state.set_state(ManualRateForm.usd)
    await message.answer("Теперь введите новый курс <b>USD</b>:")


@router.message(ManualRateForm.usd)
async def admin_rate_usd(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await state.clear()
        return
    from utils import parse_number
    val = parse_number(message.text or "")
    if not val:
        await message.answer("Число, напр. 95.5")
        return
    data = await state.get_data()
    
    import config
    config.CNY_RATE = data["new_cny"]
    config.USD_RATE = val
    
    # Save to .env so it persists across reboots
    import os
    env_path = os.path.join(os.path.dirname(config.__file__), ".env")
    try:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []
        with open(env_path, "w", encoding="utf-8") as f:
            cny_found, usd_found = False, False
            for line in lines:
                if line.startswith("CNY_RATE="):
                    f.write(f"CNY_RATE={config.CNY_RATE}\n")
                    cny_found = True
                elif line.startswith("USD_RATE="):
                    f.write(f"USD_RATE={config.USD_RATE}\n")
                    usd_found = True
                else:
                    f.write(line)
            if not cny_found: f.write(f"CNY_RATE={config.CNY_RATE}\n")
            if not usd_found: f.write(f"USD_RATE={config.USD_RATE}\n")
    except Exception:
        pass

    await state.clear()
    from keyboards import staff_panel_inline
    await message.answer(
        f"✅ Новые курсы сохранены в конфиг:\n"
        f"CNY: {config.CNY_RATE}\n"
        f"USD: {config.USD_RATE}",
        reply_markup=staff_panel_inline()
    )


@router.message(StaffForm.broadcast)
async def staff_broadcast_message(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await state.clear()
        return

    user_ids = await db.get_all_user_ids()
    sent, failed = 0, 0

    text_to_save = message.text or message.caption or ""
    for uid in user_ids:
        try:
            if message.photo:
                await message.bot.send_photo(
                    uid,
                    message.photo[-1].file_id,
                    caption=message.caption,
                )
            else:
                await message.bot.send_message(uid, text_to_save)
            if text_to_save:
                await db.add_notification(uid, text_to_save)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📢 Готово · {sent} ок · {failed} err",
        reply_markup=main_menu_inline(),
    )

