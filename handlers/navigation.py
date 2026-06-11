from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from handlers.ui import edit_home, send_home, show_panel
from handlers.user import TrackForm, show_order_guide, start_order_form, start_calculator_flow
from keyboards import order_flow_inline
from texts import screen as tscreen
from keyboards import (
    BTN_MENU_HOME,
    LEGACY_TO_NAV,
    contacts_inline,
    delivery_inline,
    links_inline,
    main_menu_inline,
    more_menu_inline,
    news_inline,
    orders_list_inline,
    settings_inline,
)
from services import cbr
from texts import (
    about_service,
    contacts_text,
    delivery_info,
    links_text,
    more_menu_title,
    news_text,
    orders_empty,
    orders_list_title,
    screen,
    support_text,
)
from utils import format_rate_message

router = Router()


@router.message(Command("menu"))
@router.message(F.text == BTN_MENU_HOME)
async def cmd_menu_home(message: Message, state: FSMContext) -> None:
    await send_home(message, state)


@router.message(F.text.in_(set(LEGACY_TO_NAV.keys())))
async def legacy_menu(message: Message, state: FSMContext) -> None:
    nav = LEGACY_TO_NAV[message.text]
    if nav == "nav:order":
        await show_order_guide(message, state)
    elif nav == "nav:orders":
        await _orders_screen(message, state)
    elif nav == "nav:calc":
        await start_calculator_flow(message, state)
    elif nav == "nav:rate":
        await _rate_screen(message, state)
    elif nav == "nav:delivery":
        await message.answer(delivery_info(), reply_markup=delivery_inline())
    elif nav == "nav:contacts":
        await message.answer(contacts_text(), reply_markup=contacts_inline())
    elif nav == "nav:links":
        await message.answer(links_text(), reply_markup=links_inline())
    elif nav == "nav:news":
        await message.answer(news_text(), reply_markup=news_inline())
    elif nav == "nav:notify":
        await _notify_screen_msg(message, state)
    elif nav == "nav:settings":
        await _settings_screen_msg(message, state)
    elif nav == "nav:about":
        await message.answer(about_service(), reply_markup=more_menu_inline())
    elif nav == "nav:support":
        await message.answer(support_text(), reply_markup=contacts_inline())
    else:
        await send_home(message, state)


@router.callback_query(F.data.startswith("nav:"))
async def handle_nav(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":", 1)[1]

    if action == "home":
        await edit_home(callback, state)
        try:
            await callback.answer()
        except Exception:
            pass
        return

    if action == "order":
        try:
            await callback.answer()
        except Exception:
            pass
        await show_order_guide(callback.message, state)
        return

    if action == "catalog":
        from texts import catalog_stub
        from keyboards import more_menu_inline
        await show_panel(callback, catalog_stub(), more_menu_inline())
        return

    if action == "orders":
        await _orders_screen_cb(callback, state)
        return

    if action == "calc":
        await callback.answer()
        await start_calculator_flow(callback.message, state)
        return

    if action == "track":
        await state.clear()
        await state.set_state(TrackForm.number)
        await callback.message.edit_text(
            tscreen("Отслеживание", "Введите ваш трек-номер:"),
            reply_markup=order_flow_inline(),
        )
        await callback.answer()
        return

    if action == "rate":
        await _rate_screen_cb(callback, state)
        return

    if action == "delivery":
        await show_panel(callback, delivery_info(), delivery_inline())
        return

    if action == "contacts":
        await show_panel(callback, contacts_text(), contacts_inline())
        return

    if action == "links":
        await show_panel(callback, links_text(), links_inline())
        return

    if action == "news":
        await show_panel(callback, news_text(), news_inline())
        return

    if action == "more":
        await show_panel(callback, more_menu_title(), more_menu_inline())
        return

    if action == "notify":
        await _notify_screen_cb(callback, state)
        return

    if action == "settings":
        await _settings_screen_cb(callback, state)
        return

    if action == "about":
        await show_panel(callback, about_service(), more_menu_inline())
        return

    if action == "support":
        await show_panel(callback, support_text(), contacts_inline())
        return

    await callback.answer()


@router.callback_query(F.data == "info:rules")
async def cb_info_rules(callback: CallbackQuery, state: FSMContext) -> None:
    import config
    from texts import url_link
    text = (
        "📚 <b>Юридическая информация</b>\n\n"
        f"1. {url_link('Пользовательское соглашение', config.TERMS_URL)}\n"
        f"2. {url_link('Политика конфиденциальности', config.POLICY_URL)}"
    )
    from keyboards import links_inline
    from handlers.ui import show_panel
    await show_panel(callback, text, links_inline())


@router.callback_query(F.data == "order:begin")
async def cb_order_begin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await start_order_form(callback.message, state)


@router.callback_query(F.data == "flow:done")
async def flow_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()


@router.callback_query(F.data == "flow:cancel")
async def flow_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await edit_home(callback, state)
    await callback.answer("Отменено")


async def _orders_screen(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await db.get_orders_by_user(message.from_user.id)
    text = orders_empty() if not rows else orders_list_title(len(rows))
    await message.answer(text, reply_markup=orders_list_inline(rows))


async def _orders_screen_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    rows = await db.get_orders_by_user(callback.from_user.id)
    text = orders_empty() if not rows else orders_list_title(len(rows))
    await show_panel(callback, text, orders_list_inline(rows))


async def _rate_screen(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(await format_rate_message(), reply_markup=main_menu_inline())


async def _rate_screen_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = await format_rate_message()
    markup = main_menu_inline()
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


async def _notify_screen_msg(message: Message, state: FSMContext) -> None:
    await state.clear()
    notifs = await db.get_notifications(message.from_user.id, limit=5)
    if not notifs:
        text = "📭 <b>Почтовый ящик</b>\n─────────────────\nПусто"
    else:
        text = "📭 <b>Почтовый ящик</b>\n─────────────────\n\n"
        for i, n in enumerate(notifs):
            date = n["created_at"][:16]
            text += f"📅 <i>{date}</i>\n{n['message']}\n\n"
    from keyboards import more_menu_inline
    await message.answer(text, reply_markup=more_menu_inline())


async def _settings_screen_msg(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_user(message.from_user.id)
    on = bool(user["notify_orders"]) if user else True
    await message.answer(
        f"⚙️ Уведомления: <b>{'вкл' if on else 'выкл'}</b>",
        reply_markup=settings_inline(on),
    )


async def _notify_screen_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    notifs = await db.get_notifications(callback.from_user.id, limit=5)
    if not notifs:
        text = "📭 <b>Почтовый ящик</b>\n─────────────────\nПусто"
    else:
        text = "📭 <b>Почтовый ящик</b>\n─────────────────\n\n"
        for i, n in enumerate(notifs):
            date = n["created_at"][:16]
            text += f"📅 <i>{date}</i>\n{n['message']}\n\n"
    from keyboards import more_menu_inline
    await show_panel(callback, text, more_menu_inline())


async def _settings_screen_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    on = bool(user["notify_orders"]) if user else True
    await show_panel(
        callback,
        f"⚙️ <b>Настройки</b>\nУведомления: <b>{'вкл' if on else 'выкл'}</b>",
        settings_inline(on),
    )
