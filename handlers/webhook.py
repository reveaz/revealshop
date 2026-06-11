"""
handlers/webhook.py
===================
Эндпоинт ResultURL для приёма уведомлений об оплате от Robokassa.

Robokassa отправляет POST/GET на ResultURL с параметрами:
    OutSum, InvId, SignatureValue (+доп. Shp_* параметры).

Подпись: MD5(OutSum:InvId:Password2)
Ответ при успехе: «OK{InvId}» (plain text).

Запуск: aiohttp-сервер встроен в main.py.
"""

import logging

from aiohttp import web

import database as db
from services.robokassa import verify_result_signature

logger = logging.getLogger(__name__)

# Глобальная ссылка на объект бота — заполняется при запуске
_bot = None


def set_bot(bot) -> None:
    """Вызывается из main.py, чтобы webhook мог отправлять сообщения."""
    global _bot
    _bot = bot


async def handle_robokassa_result(request: web.Request) -> web.Response:
    """
    POST /webhook/robokassa  (ResultURL)

    1. Валидация подписи MD5/SHA256
    2. При успехе:
       - payments.status → 'paid'
       - orders.status   → 'Выкуплен'
       - Уведомление пользователю + админам
    3. Ответ: «OK{InvId}»
    """
    # Robokassa может отправлять как POST form, так и GET query
    if request.method == "POST":
        try:
            data = await request.post()
        except Exception:
            data = request.query
    else:
        data = request.query

    out_sum = str(data.get("OutSum", ""))
    inv_id = str(data.get("InvId", ""))
    received_sign = str(data.get("SignatureValue", ""))

    if not out_sum or not inv_id:
        logger.warning("Robokassa ResultURL: отсутствуют OutSum/InvId")
        return web.Response(text="BAD REQUEST", status=400)

    # ── Валидация подписи ──
    if not verify_result_signature(out_sum, inv_id, received_sign):
        logger.warning("Robokassa ResultURL: невалидная подпись (InvId=%s)", inv_id)
        return web.Response(text="BAD SIGN", status=403)

    logger.info("Robokassa ResultURL: InvId=%s OutSum=%s ✓", inv_id, out_sum)

    order_id = int(inv_id)

    # 1. Обновляем статус платежа
    payment_id = str(order_id)
    await db.update_payment_status(payment_id, "paid")

    # 2. Переводим заказ в «Выкуплен»
    order = await db.update_order_status(order_id, "Выкуплен")

    # 3. Уведомляем пользователя
    if order and _bot:
        user = await db.get_user(order["user_id"])
        if user and user["notify_orders"]:
            try:
                await _bot.send_message(
                    order["user_id"],
                    f"✅ <b>Заказ #{order_id}</b> — оплата получена!\n\n"
                    f"Статус обновлён → <b>Выкуплен</b>\n"
                    f"Ваш товар будет выкуплен в течение 24 ч.",
                )
            except Exception as e:
                logger.error("Не удалось уведомить user %s: %s", order["user_id"], e)

    # 4. Уведомляем админов
    if _bot:
        import config

        for admin_id in config.ADMIN_IDS:
            try:
                await _bot.send_message(
                    admin_id,
                    f"💰 <b>Оплата получена (Robokassa)</b>\n"
                    f"Заказ #{order_id} · {out_sum} ₽",
                )
            except Exception:
                pass

    # Robokassa требует ответ «OK{InvId}»
    return web.Response(text=f"OK{inv_id}")


def create_webhook_app() -> web.Application:
    """Создаёт aiohttp-приложение с маршрутом для Robokassa ResultURL."""
    app = web.Application()
    app.router.add_post("/webhook/robokassa", handle_robokassa_result)
    app.router.add_get("/webhook/robokassa", handle_robokassa_result)
    
    import pathlib
    import config
    webapp_dir = config._ROOT / "webapp"
    app.router.add_static("/app/", path=str(webapp_dir), name="webapp")
    
    return app
