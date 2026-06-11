"""
handlers/webhook.py
===================
Эндпоинт для приёма ResultURL (webhook) от Prodamus.

Prodamus отправляет POST-запрос с JSON при успешной/неуспешной оплате.
Заголовок «Sign» содержит HMAC-SHA256 подпись тела.

Запуск: aiohttp-сервер встроен в main.py через start_webhook_server().
"""

import logging

from aiohttp import web

import database as db
from services.prodamus import verify_prodamus_signature

logger = logging.getLogger(__name__)

# Глобальная ссылка на объект бота — заполняется при запуске
_bot = None


def set_bot(bot) -> None:
    """Вызывается из main.py, чтобы webhook мог отправлять сообщения."""
    global _bot
    _bot = bot


async def handle_prodamus_webhook(request: web.Request) -> web.Response:
    """
    POST /webhook/prodamus

    Тело — JSON от Prodamus. Заголовок «Sign» — HMAC-SHA256.
    При успешной оплате:
        1. payments.status → 'paid'
        2. orders.status   → 'Выкуплен'
        3. Уведомление пользователю
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Prodamus webhook: невалидный JSON")
        return web.json_response({"error": "invalid json"}, status=400)

    # ── Валидация подписи ──
    received_sign = request.headers.get("Sign", "")
    if not received_sign:
        received_sign = body.get("signature", "")

    if not verify_prodamus_signature(body, received_sign):
        logger.warning("Prodamus webhook: невалидная подпись")
        return web.json_response({"error": "invalid signature"}, status=403)

    # ── Обработка ──
    payment_id = body.get("order_num") or body.get("order_id", "")
    payment_status = str(body.get("payment_status", "")).lower()

    if not payment_id:
        logger.warning("Prodamus webhook: нет order_id / order_num")
        return web.json_response({"error": "missing order_id"}, status=400)

    logger.info(
        "Prodamus webhook: payment_id=%s status=%s", payment_id, payment_status
    )

    payment_row = await db.get_payment(payment_id)
    if not payment_row:
        logger.warning("Prodamus webhook: платёж %s не найден в БД", payment_id)
        return web.json_response({"error": "payment not found"}, status=404)

    order_id = payment_row["order_id"]

    if payment_status == "success":
        # 1. Обновляем статус платежа
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

        # Уведомляем админов
        if _bot:
            import config
            for admin_id in config.ADMIN_IDS:
                try:
                    await _bot.send_message(
                        admin_id,
                        f"💰 <b>Оплата получена</b>\n"
                        f"Заказ #{order_id} · payment_id={payment_id}",
                    )
                except Exception:
                    pass

    elif payment_status in ("fail", "failed", "cancel"):
        await db.update_payment_status(payment_id, "failed")
        logger.info("Платёж %s — неуспешный (%s)", payment_id, payment_status)

    return web.json_response({"status": "ok"})


def create_webhook_app() -> web.Application:
    """Создаёт aiohttp-приложение с маршрутом для Prodamus webhook."""
    app = web.Application()
    app.router.add_post("/webhook/prodamus", handle_prodamus_webhook)
    return app
