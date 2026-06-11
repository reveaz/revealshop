import config

BRAND = "RevealLorder"
DOT = "🔵"
SEP = "━━━━━━━━━━━━━"


def tg(label: str, username: str) -> str:
    user = username.lstrip("@")
    return f'<a href="https://t.me/{user}">{label}</a>'


def url_link(label: str, url: str) -> str:
    return f'<a href="{url}">{label}</a>'


def screen(title: str, body: str = "") -> str:
    if body:
        return f"{DOT} <b>{title}</b>\n{SEP}\n{body}"
    return f"{DOT} <b>{title}</b>\n{SEP}"


def progress_bar(step: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return ""
    filled = round(step / total * width)
    filled = max(0, min(width, filled))
    return "▰" * filled + "▱" * (width - filled)


FAQ_PAYMENT = screen(
    "Оплата",
    "1️⃣ Заказ в боте\n"
    "2️⃣ Ожидание в очереди\n"
    "3️⃣ Расчёт по курсу ЦБ + комиссия\n"
    "4️⃣ Выкуп в течение 24 ч\n"
    "5️⃣ Доставка — после взвешивания\n\n"
    "⚠️ Проверяйте реквизиты перед оплатой",
)

GEOGRAPHY = screen(
    "География",
    "🇷🇺 Россия  ·  🇧🇾 Беларусь  ·  🇰🇿 Казахстан\n"
    "🇺🇿 Узбекистан  ·  🇰🇬 Кыргызстан  ·  🌍 др. СНГ",
)


def welcome(name: str) -> str:
    first = name.split()[0] if name and name.split() else "друг"
    return (
        f"Привет, <b>{first}</b> 👋\n\n"
        f"Выкуп из 🇨🇳 · доставка в СНГ\n\n"
        f"🕐 {config.WORK_HOURS}\n\n"
        f"⚠️ <i>Продолжая использование бота, вы автоматически соглашаетесь с "
        f"{url_link('Пользовательским соглашением', config.TERMS_URL)} и "
        f"{url_link('Политикой конфиденциальности', config.POLICY_URL)}.</i>"
    )


def about_service() -> str:
    t = int(config.COMMISSION_THRESHOLD_CNY)
    return screen(
        "О сервисе",
        f"Комиссия <b>5%</b> до {t} ¥ · <b>7%</b> от {t} ¥\n"
        f"Курс ЦБ · доставка <b>{config.DELIVERY_USD_PER_KG:.0f}$/кг</b>\n"
        f"Лог. сбор <b>{int(config.LOGISTICS_FEE_RUB)} ₽</b>\n"
        f"Срок 9–15 дней до Астаны · бот 24/7\n\n"
        f"<b>Юридическая информация</b>\n"
        f"ИП Фамилия Имя Отчество\n"
        f"ИИН: 000000000000\n"
        f"Юр. адрес: г. Астана, ул. …\n\n"
        f"Использование бота означает согласие с {url_link('Пользовательским соглашением', config.TERMS_URL)}."
    )


def delivery_info() -> str:
    return screen(
        "Доставка",
        f"🚛 Фура · <b>{config.DELIVERY_USD_PER_KG:.0f} $/кг</b>\n"
        "⏱ 9–15 дней до Астаны\n"
        f"⚖️ Мин. <b>{config.MIN_WEIGHT_KG:.0f} кг</b> (округление вверх)\n\n"
        "Далее — транспортная компания в ваш город",
    )


def contacts_text() -> str:
    return (
        f"{DOT} <b>Контакты</b>\n{SEP}\n\n"
        f"<b>ИП Фамилия Имя Отчество</b>\n"
        f"ИИН: 000000000000\n"
        f"Юр. адрес: г. Астана, ул. …\n"
        f"E-mail: info@revealshop.kz"
    )


def support_text() -> str:
    return screen(
        "Поддержка",
        f"Споры → {tg('менеджер', 'revealLmanager')}\n"
        f"Вопросы → {tg(config.SUPPORT_USERNAME, config.SUPPORT_USERNAME)}\n\n"
        "⚡️ Ответ ~1 часа · без спама в ЛС",
    )


def links_text() -> str:
    return f"{DOT} <b>Полезные ссылки</b>\n{SEP}"


def news_text() -> str:
    return screen(
        "Новости",
        "Обновления сервиса и отзывы вы можете найти на нашем канале",
    )


def orders_empty() -> str:
    return screen("Мои заказы", "Пока пусто\n\nОформите первый заказ ↓")


def orders_list_title(count: int) -> str:
    return screen("Мои заказы", f"Всего: <b>{count}</b>")


def order_created(order_id: int, cargo_type: str, weight: float, city_to: str, calc: dict | None = None) -> str:
    weight_str = f"  ·  ⚖️ {weight} кг" if weight > 0 else ""
    body = (
        f"✅ Принят в обработку\n\n"
        f"📦 {cargo_type}{weight_str}\n"
        f"📍 {city_to}\n\n"
    )
    if calc:
        from utils import fmt_calc_result_body
        body += f"<b>📊 Предварительный расчёт</b>\n{fmt_calc_result_body(calc)}\n\n"

    body += (
        f"⚠️ <i>Оплачивая заказ, вы подтверждаете согласие с "
        f"{url_link('Пользовательским соглашением', config.TERMS_URL)} "
        f"и отказываетесь от претензий по возврату цифрового товара.</i>"
    )
    return screen(f"Заказ #{order_id}", body)


def stats_text(users: int, pending: int) -> str:
    return screen(
        "Статистика",
        f"👥 Пользователей — <b>{users}</b>\n"
        f"📦 К обработке — <b>{pending}</b>",
    )


def staff_panel() -> str:
    return screen("Панель сотрудника")


def admin_header(users: int, pending: int) -> str:
    return screen(
        "Админ",
        f"👥 {users} польз.  ·  📦 {pending} в работе",
    )


def more_menu_title() -> str:
    return screen("Ещё", "Ссылки · настройки · поддержка")


def catalog_stub() -> str:
    return screen(
        "🔥 Каталог хитов",
        "Раздел в разработке\n\n"
        "Здесь скоро появятся готовые карточки товаров\n"
        "с фото, описанием и финальной ценой \"под ключ\".\n\n"
        "Следите за обновлениями в нашем канале 👇",
    )
