import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    import os

    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN не найден в .env")
        sys.exit(1)

    await db.init_db()

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    from services.auto_track import auto_track_loop

    logger.info("Бот запущен. Админы: %s", config.ADMIN_IDS or "не заданы")
    logger.info("Курсы: CNY=%s USD=%s (Вручную из config.py)", config.CNY_RATE, config.USD_RATE)

    # Start auto-tracking background task
    asyncio.create_task(auto_track_loop(bot))
    logger.info("Авто-трекинг запущен")

    # Start Prodamus webhook server (if configured)
    if config.PRODAMUS_API_KEY:
        from aiohttp import web
        from handlers.webhook import create_webhook_app, set_bot

        set_bot(bot)
        webhook_app = create_webhook_app()
        runner = web.AppRunner(webhook_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", config.WEBHOOK_PORT)
        await site.start()
        logger.info("Prodamus webhook слушает на порту %s", config.WEBHOOK_PORT)
    else:
        logger.info("PRODAMUS_API_KEY не задан — webhook-сервер не запущен")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

