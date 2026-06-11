from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import config
import database as db
from handlers.common import ONBOARDING_STEPS, calc_kwargs, calculator_intro
from handlers.ui import remove_reply_keyboard, send_home
from services.tracker import get_tracking_info
from keyboards import (
    CANCEL_TEXTS,
    calc_result_inline,
    main_menu_inline,
    onboarding_inline,
    order_cancel_inline,
    order_guide_inline,
)
from texts import SEP, order_created, screen
from utils import (
    build_calculation,
    fmt_calc_result,
    parse_number,
)

router = Router()


class OrderForm(StatesGroup):
    cargo_type = State()
    cost_cny = State()
    city_to = State()


class CalculatorForm(StatesGroup):
    cost_cny = State()
    weight = State()


class CommentForm(StatesGroup):
    text = State()


class TrackForm(StatesGroup):
    number = State()


async def notify_admins_new_order(
    bot, order_id: int, user, cargo_type: str, weight: float, city_to: str, cost_cny: float = 0.0
) -> None:
    weight_str = f" · ⚖️ {weight} кг" if weight > 0 else ""
    cost_str = f" · 💰 {cost_cny} ¥" if cost_cny > 0 else ""
    text = (
        f"🆕 <b>#{order_id}</b>\n"
        f"📦 {cargo_type}{weight_str}{cost_str}\n"
        f"📍 → {city_to}\n"
        f"{user.full_name} · <code>{user.id}</code>"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


async def show_order_guide(message: Message, state: FSMContext, edit: bool = False) -> None:
    """Show pre-order tutorial screen with video guide link."""
    await state.clear()
    from aiogram.types import FSInputFile
    text = screen(
        "Как заказать",
        "Посмотрите короткий гайд перед\n"
        "оформлением первого заказа 👇\n\n"
        "⚠️ <i>Запрещены тестовые заказы — за это можно получить блокировку в боте.</i>",
    )
    kb = order_guide_inline()
    if config.BANNER_GUIDE.exists():
        try:
            await message.answer_photo(
                FSInputFile(config.BANNER_GUIDE),
                caption=text,
                reply_markup=kb,
            )
            return
        except Exception:
            pass
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb)


async def start_order_form(message: Message, state: FSMContext) -> None:
    """Start the actual order form (step 1)."""
    await state.clear()
    await state.set_state(OrderForm.cargo_type)
    text = screen(
        "Новый заказ",
        "Шаг 1/3 · <b>Тип груза</b>\n\n"
        "Опишите что за товар:\n"
        "<i>одежда, обувь, смартфон</i>\n\n"
        "⚠️ <i>Запрещены тестовые заказы — за это можно получить блокировку в боте.</i>",
    )
    await message.answer(text, reply_markup=order_cancel_inline())


async def start_calculator_flow(message: Message, state: FSMContext, edit: bool = False) -> None:
    await state.clear()
    await state.set_state(CalculatorForm.cost_cny)
    text = calculator_intro()
    if edit:
        try:
            await message.edit_text(text, reply_markup=order_cancel_inline())
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=order_cancel_inline())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user:
        await db.upsert_user(user.id, user.username, user.full_name)
        row = await db.get_user(user.id)
        if row and not row["onboarding_done"]:
            await remove_reply_keyboard(message)
            await message.answer(
                ONBOARDING_STEPS[0],
                reply_markup=onboarding_inline(1),
            )
            return
    await send_home(message, state)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нет активного действия.")
        return
    await send_home(message, state)


# ── Order form: Step 1 — Cargo type ──

@router.message(OrderForm.cargo_type)
async def order_cargo_type(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return

    cargo = (message.text or "").strip()
    if not cargo or len(cargo) < 2:
        await message.answer(
            "❌ Укажите тип груза (напр. одежда, техника)",
            reply_markup=order_cancel_inline(),
        )
        return

    await state.update_data(cargo_type=cargo, weight=0.0)
    await state.set_state(OrderForm.cost_cny)
    await message.answer(
        screen("Новый заказ", "Шаг 2/3 · <b>Стоимость (¥)</b>\n\nУкажите цену товара в юанях:"),
        reply_markup=order_cancel_inline(),
    )


# ── Order form: Step 2 — Cost ──

@router.message(OrderForm.cost_cny)
async def order_cost_cny(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return
    cost = parse_number(message.text or "")
    if cost is None:
        await message.answer("Число, напр. 150.5", reply_markup=order_cancel_inline())
        return
    await state.update_data(cost_cny=cost)
    await state.set_state(OrderForm.city_to)
    await message.answer(
        screen("Новый заказ", "Шаг 3/3 · <b>Город доставки</b>\n\nКуда доставить:"),
        reply_markup=order_cancel_inline(),
    )


# ── Order form: Step 3 — City (final) ──

@router.message(OrderForm.city_to)
async def order_city_to(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return
    city_to = (message.text or "").strip()
    if not city_to:
        await message.answer("Укажите город", reply_markup=order_cancel_inline())
        return

    data = await state.get_data()
    cost_cny = data.get("cost_cny", 0.0)
    order_id = await db.create_order(
        user_id=message.from_user.id,
        cargo_type=data["cargo_type"],
        weight=data.get("weight", 0.0),
        cost_cny=cost_cny,
        city=city_to,
    )
    
    # Generate calculation
    kwargs = calc_kwargs()
    import config
    kwargs["cny_rate"] = config.CNY_RATE
    kwargs["usd_rate"] = config.USD_RATE
    kwargs["kzt_per_rub"] = config.KZT_PER_RUB
    calc = build_calculation(cost_cny, 0.0, **kwargs)

    await state.clear()
    await notify_admins_new_order(
        message.bot, order_id, message.from_user,
        data["cargo_type"], 0.0, city_to, cost_cny
    )
    
    # Combined single message with no web page preview
    await message.answer(
        order_created(order_id, data["cargo_type"], 0.0, city_to, calc=calc),
        reply_markup=main_menu_inline(),
        disable_web_page_preview=True
    )


@router.message(CommentForm.text)
async def save_comment(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return
    data = await state.get_data()
    order_id = data.get("order_id")
    if order_id:
        await db.set_order_comment(order_id, message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer(
        f"💬 Сохранено · #{order_id}" if order_id else "Готово",
        reply_markup=main_menu_inline(),
    )


@router.message(CalculatorForm.cost_cny)
async def calculator_cost(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return
    cost = parse_number(message.text or "")
    if cost is None:
        await message.answer("Введите ¥", reply_markup=order_cancel_inline())
        return
    await state.update_data(cost_cny=cost)
    await state.set_state(CalculatorForm.weight)
    await message.answer(
        screen("Калькулятор", "Шаг 2 · вес (кг):"),
        reply_markup=order_cancel_inline(),
    )


@router.message(CalculatorForm.weight)
async def calculator_weight(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return
    weight = parse_number(message.text or "")
    if weight is None:
        await message.answer("Число, напр. 12", reply_markup=order_cancel_inline())
        return

    data = await state.get_data()
    
    kwargs = calc_kwargs()
    import config
    kwargs["cny_rate"] = config.CNY_RATE
    kwargs["usd_rate"] = config.USD_RATE
    kwargs["kzt_per_rub"] = config.KZT_PER_RUB
    
    calc = build_calculation(data["cost_cny"], weight, **kwargs)
    await state.clear()
    await message.answer(
        fmt_calc_result(calc),
        reply_markup=calc_result_inline(),
    )


@router.message(TrackForm.number)
async def track_number(message: Message, state: FSMContext) -> None:
    if message.text in CANCEL_TEXTS or message.text == "🏠 Меню":
        await send_home(message, state)
        return

    raw = (message.text or "").strip()
    if not raw or len(raw) < 5:
        await message.answer(
            "❌ Некорректный трек-номер. Попробуйте ещё раз:",
            reply_markup=order_cancel_inline(),
        )
        return

    wait = await message.answer("🔍 Ищу посылку… Это может занять до 2 минут.")

    result = await get_tracking_info(raw)

    try:
        await wait.delete()
    except Exception:
        pass

    if result is None:
        await state.clear()
        await message.answer(
            screen(
                "Трек-номер не найден",
                f"<code>{raw}</code>\n\n"
                "Посылка не найдена или трек ещё не зарегистрирован.\n"
                "Проверьте номер и попробуйте позже.",
            ),
            reply_markup=main_menu_inline(),
        )
        return

    await state.clear()
    body = (
        f"{result.emoji} <b>{result.status_ru}</b>\n"
        f"{SEP}\n"
        f"📦 <code>{result.number}</code>\n\n"
        f"📝 {result.latest_event}\n"
    )

    await message.answer(
        screen("Отслеживание", body),
        reply_markup=main_menu_inline(),
    )

