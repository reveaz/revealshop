"""
bot.py
======
Telegram-бот с автоматическим получением курса RUB от ForteBusiness.

Зависимости:
    pip install python-telegram-bot playwright httpx beautifulsoup4
    playwright install chromium

Запуск:
    BOT_TOKEN=ваш_токен python bot.py
"""

import os
import asyncio
import logging
from datetime import datetime

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from forte_rates import rates_cache, Rates

# ──────────────────────────────────────────────
# Настройка логирования
# ──────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Конфиг
# ──────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")
REFRESH_INTERVAL = 1800  # секунды (30 мин)


# ──────────────────────────────────────────────
# Команды бота
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я показываю актуальный курс RUB/KZT от ForteBusiness.\n\n"
        "📌 Команды:\n"
        "  /rate — текущий курс\n"
        "  /refresh — принудительно обновить курс\n"
    )


async def cmd_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущий (закешированный) курс."""
    await update.message.reply_text("⏳ Получаю курс...")

    rates = await rates_cache.get()

    if rates is None:
        await update.message.reply_text(
            "❌ Не удалось получить курс.\n"
            "Попробуйте /refresh или проверьте позже."
        )
        return

    age_min = int(rates.age_seconds() // 60)
    updated = datetime.fromtimestamp(rates.updated_at).strftime("%H:%M")

    await update.message.reply_text(
        f"{rates}\n\n"
        f"🕐 Обновлено в {updated} (МСК {age_min} мин назад)"
    )


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Принудительно обновляет курс с сайта."""
    await update.message.reply_text("🔄 Обновляю курс с ForteBusiness...")

    rates = await rates_cache.force_refresh()

    if rates is None:
        await update.message.reply_text(
            "❌ Не удалось получить курс.\n"
            "Возможно, сайт ForteBusiness недоступен."
        )
        return

    await update.message.reply_text(
        f"✅ Курс обновлён!\n\n{rates}"
    )


# ──────────────────────────────────────────────
# Автоматическое фоновое обновление
# ──────────────────────────────────────────────

async def auto_refresh_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Фоновая задача — обновляет курс раз в REFRESH_INTERVAL секунд."""
    logger.info("Авто-обновление курса ForteBusiness...")
    rates = await rates_cache.force_refresh()
    if rates:
        logger.info(f"Курс обновлён: покупка={rates.buy}, продажа={rates.sell}")
    else:
        logger.warning("Авто-обновление не дало результата")


# ──────────────────────────────────────────────
# Запуск
# ──────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Устанавливает меню команд и делает первый запрос курса."""
    await application.bot.set_my_commands([
        BotCommand("start", "Начало работы"),
        BotCommand("rate", "Текущий курс RUB/KZT"),
        BotCommand("refresh", "Принудительно обновить курс"),
    ])
    # Первая загрузка при старте
    logger.info("Первичная загрузка курса...")
    await rates_cache.force_refresh()


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Регистрируем команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rate", cmd_rate))
    app.add_handler(CommandHandler("refresh", cmd_refresh))

    # Фоновое авто-обновление каждые 30 минут
    app.job_queue.run_repeating(
        auto_refresh_job,
        interval=REFRESH_INTERVAL,
        first=REFRESH_INTERVAL,   # первый раз через 30 мин (сразу грузим в post_init)
    )

    logger.info("Бот запущен. Ожидаю команды...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
