from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import config
import database as db

CB_HOME = "nav:home"

BTN_MENU_HOME = "🏠 Меню"
BTN_DONE = "✅ Готово"
BTN_CANCEL = "❌ Отмена"

CANCEL_TEXTS = {BTN_CANCEL, "Отмена", "❌ Отмена", "/cancel"}

LEGACY_TO_NAV = {
    "🔗 Выкуп по ссылке (Pro)": "nav:order",
    "📋 Мои заказы": "nav:orders",
    "🧮 Калькулятор": "nav:calc",
    "💱 Актуальный курс": "nav:rate",
    "👥 Контакты": "nav:contacts",
    "🔗 Полезные ссылки": "nav:links",
    "📰 Новости": "nav:news",
    "🔔 Уведомления": "nav:notify",
    "⚙️ Настройки": "nav:settings",
    "🚚 Доставка": "nav:delivery",
    "ℹ️ О сервисе": "nav:about",
    "💬 Поддержка": "nav:support",
}


def _home_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="🏠 Меню", callback_data=CB_HOME)]


def nav_footer_inline(back_data: str = "staff:panel") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=back_data)
    b.button(text="🏠 Меню", callback_data=CB_HOME)
    b.adjust(2)
    return b.as_markup()


def main_menu_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔥 Каталог хитов", web_app=WebAppInfo(url=config.WEBAPP_URL))
    b.button(text="🔗 Выкуп по ссылке (Pro)", callback_data="nav:order")
    b.button(text="📋 Мои заказы", callback_data="nav:orders")
    b.button(text="🧮 Калькулятор", callback_data="nav:calc")
    b.button(text="📈 Актуальный курс", callback_data="nav:rate")
    b.button(text="👤 Контакты", callback_data="nav:contacts")
    b.button(text="🔗 Полезные ссылки", callback_data="nav:links")
    b.button(text="📰 Новости", callback_data="nav:news")
    b.button(text="📢 Уведомления", callback_data="nav:notify")
    b.button(text="⚙️ Настройки", callback_data="nav:settings")
    b.adjust(1, 1, 2, 2, 2, 2)
    return b.as_markup()


def more_menu_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔗 Ссылки", callback_data="nav:links")
    b.button(text="🔔 Алерты", callback_data="nav:notify")
    b.button(text="⚙️ Настройки", callback_data="nav:settings")
    b.button(text="ℹ️ О сервисе", callback_data="nav:about")
    b.button(text="💬 Поддержка", callback_data="nav:support")
    b.adjust(2)
    b.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="nav:home"),
    )
    return b.as_markup()


def menu_reply() -> ReplyKeyboardMarkup:
    return (
        ReplyKeyboardBuilder()
        .row(KeyboardButton(text=BTN_MENU_HOME))
        .as_markup(resize_keyboard=True, is_persistent=False)
    )


def order_flow_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✓ Готово", callback_data="flow:done"),
        InlineKeyboardButton(text="✕ Отмена", callback_data="flow:cancel"),
    )
    return b.as_markup()


def order_cancel_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="✕ Отмена", callback_data="flow:cancel"))
    return b.as_markup()


def order_guide_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if config.GUIDE_VIDEO_URL:
        b.row(InlineKeyboardButton(text="🎬 Смотреть гайд", url=config.GUIDE_VIDEO_URL))
    b.row(InlineKeyboardButton(text="▶️ Оформить заказ", callback_data="order:begin"))
    b.row(InlineKeyboardButton(text="🏠 Меню", callback_data=CB_HOME))
    return b.as_markup()


def orders_list_inline(orders: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for row in orders[:8]:
        b.button(
            text=db.order_button_label(row["id"], row["status"]),
            callback_data=f"order:view:{row['id']}",
        )
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔗 Выкуп по ссылке", callback_data="nav:order"))
    b.row(InlineKeyboardButton(text="🏠 Меню", callback_data=CB_HOME))
    return b.as_markup()


def order_detail_inline(order_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💬 Комментарий", callback_data=f"order:comment:{order_id}"),
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"order:delete:{order_id}"),
    )
    b.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="nav:orders"),
        InlineKeyboardButton(text="🏠 Меню", callback_data=CB_HOME),
    )
    return b.as_markup()


def contacts_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔍 Подбор", url="https://t.me/revealLsearch")
    b.button(text="💰 Выкуп", url="https://t.me/revealLbuy")
    b.button(text="👨‍💼 Менеджер", url="https://t.me/revealLmanager")
    b.button(text="💬 Поддержка", url=f"https://t.me/{config.SUPPORT_USERNAME}")
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🏠 Меню", callback_data=CB_HOME))
    return b.as_markup()


def links_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📢 Отзывы", url=config.NEWS_CHANNEL_URL)
    b.button(text="🎵 TikTok", url=config.TIKTOK_URL)
    b.button(text="🔍 Подбор", url="https://t.me/revealLsearch")
    b.button(text="💰 Выкуп", url="https://t.me/revealLbuy")
    b.button(text="👨‍💼 Менеджер", url="https://t.me/revealLmanager")
    b.button(text="📚 Правила", callback_data="info:rules")
    b.adjust(2)
    b.row(*_home_row())
    return b.as_markup()


def news_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📢 Канал", url="https://t.me/revealshop")
    b.row(*_home_row())
    return b.as_markup()


def settings_inline(notify_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    icon = "🔔" if notify_on else "🔕"
    b.button(text=f"{icon} Уведомления", callback_data="settings:notify:toggle")
    b.button(text="📘 Обучение", callback_data="onboard:start")
    b.adjust(2)
    b.row(*_home_row())
    return b.as_markup()


def delivery_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🌍 Страны", callback_data="info:geo")
    b.button(text="💳 Оплата", callback_data="info:pay")
    b.row(*_home_row())
    return b.as_markup()


def calc_result_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🧮 Новый расчет", callback_data="nav:calc")
    b.button(text="🔗 Заказать по ссылке", callback_data="nav:order")
    b.adjust(1)
    b.row(*_home_row())
    return b.as_markup()


def onboarding_inline(step: int, total: int = 4) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if step < total:
        b.button(text=f"Далее · {step}/{total}", callback_data=f"onboard:{step + 1}")
    else:
        b.button(text="✓ Готово", callback_data="onboard:done")
    b.button(text="Пропустить", callback_data="onboard:skip")
    b.adjust(2)
    return b.as_markup()


def staff_panel_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📦 Заказы", callback_data="staff:orders")
    b.button(text="📢 Рассылка", callback_data="staff:broadcast")
    b.button(text="💱 Курсы", callback_data="staff:rates")
    b.button(text="📊 Стат.", callback_data="staff:stats")
    b.adjust(2)
    b.row(*_home_row())
    return b.as_markup()


def admin_orders_inline(orders: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for row in orders[:10]:
        b.button(
            text=db.order_button_label(row["id"], row["status"]),
            callback_data=f"staff:order:{row['id']}",
        )
    b.adjust(1)
    b.row(InlineKeyboardButton(text="◀️ Панель", callback_data="staff:panel"))
    return b.as_markup()


def staff_order_status_inline(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    idx = db.status_index(current_status)
    cancel_idx = len(db.ORDER_STATUSES) - 1

    if current_status == "Отменён":
        b.row(
            InlineKeyboardButton(
                text="↩ В обработку",
                callback_data=f"staff:st:{order_id}:0",
            )
        )
    else:
        nav: list[InlineKeyboardButton] = []
        if idx > 0:
            prev = db.ORDER_STATUSES[idx - 1]
            nav.append(
                InlineKeyboardButton(
                    text=f"◀ {db.STATUS_SHORT[prev]}",
                    callback_data=f"staff:st:{order_id}:{idx - 1}",
                )
            )
        if idx < cancel_idx - 1:
            nxt = db.ORDER_STATUSES[idx + 1]
            nav.append(
                InlineKeyboardButton(
                    text=f"{db.STATUS_SHORT[nxt]} ▶",
                    callback_data=f"staff:st:{order_id}:{idx + 1}",
                )
            )
        if nav:
            b.row(*nav)
        if current_status not in db.DONE_STATUSES:
            b.row(
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"staff:st:{order_id}:{cancel_idx}",
                )
            )
        b.row(
            InlineKeyboardButton(
                text="⋯ Все статусы",
                callback_data=f"staff:full:{order_id}",
            )
        )

    b.row(
        InlineKeyboardButton(
            text="📍 Трек-код",
            callback_data=f"staff:track:{order_id}",
        ),
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"staff:delete:{order_id}",
        )
    )
    b.row(
        InlineKeyboardButton(text="◀ Заказы", callback_data="staff:orders"),
        InlineKeyboardButton(text="🏠 Меню", callback_data=CB_HOME),
    )
    return b.as_markup()


def staff_order_status_full_inline(order_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for idx, status in enumerate(db.ORDER_STATUSES):
        b.button(
            text=db.STATUS_SHORT.get(status, status[:12]),
            callback_data=f"staff:st:{order_id}:{idx}",
        )
    b.adjust(3)
    b.button(text="◀ Компакт", callback_data=f"staff:order:{order_id}")
    b.row(*_home_row())
    return b.as_markup()
