"""
services/prodamus.py
====================
Адаптер для платежного шлюза Prodamus.

Документация API:  https://help.prodamus.ru/payform/integracii/rest-api
Подпись (HMAC-SHA256): https://help.prodamus.ru/payform/integracii/webhook
"""

import hashlib
import hmac
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

import config

logger = logging.getLogger(__name__)


@dataclass
class ProdamusInvoice:
    """Результат создания счёта в Prodamus."""
    payment_id: str
    payment_url: str


async def prodamus_create_invoice(
    order_id: int,
    amount: float,
    currency: str = "KZT",
    customer_phone: str = "",
    customer_email: str = "",
    description: str = "",
) -> ProdamusInvoice | None:
    """
    Создаёт ссылку на оплату через REST API Prodamus.

    Необходимые переменные окружения (config.py):
        PRODAMUS_API_URL  — базовый URL формы (напр. https://yourshop.payform.ru)
        PRODAMUS_API_KEY  — секретный ключ магазина

    Возвращает ProdamusInvoice(payment_id, payment_url) или None при ошибке.
    """
    api_url = config.PRODAMUS_API_URL
    api_key = config.PRODAMUS_API_KEY

    if not api_url or not api_key:
        logger.error("PRODAMUS_API_URL / PRODAMUS_API_KEY не заданы в .env")
        return None

    payment_id = f"order-{order_id}-{uuid.uuid4().hex[:8]}"
    if not description:
        description = f"Оплата заказа #{order_id} — RevealLorder"

    # Параметры для PayForm (GET-ссылка или REST)
    params: dict[str, Any] = {
        "order_id": payment_id,
        "customer_phone": customer_phone,
        "customer_email": customer_email or "noreply@reveallorder.com",
        "products[0][name]": description,
        "products[0][price]": str(round(amount, 2)),
        "products[0][quantity]": "1",
        "products[0][currency]": currency,
        "do": "link",  # Получить ссылку вместо формы
    }

    # Генерация подписи
    # Prodamus требует HMAC-SHA256 от отсортированных параметров
    sign_string = json.dumps(
        dict(sorted(params.items())), ensure_ascii=False, separators=(",", ":")
    )
    signature = hmac.new(
        api_key.encode(), sign_string.encode(), hashlib.sha256
    ).hexdigest()
    params["signature"] = signature

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(api_url, data=params)
            resp.raise_for_status()
            data = resp.text.strip()

            # Prodamus возвращает URL платежной страницы в теле ответа
            if data.startswith("http"):
                payment_url = data
            else:
                # Пробуем JSON
                body = resp.json()
                payment_url = body.get("payment_url") or body.get("url", "")

            if not payment_url:
                logger.error("Prodamus не вернул payment_url: %s", data[:300])
                return None

            logger.info(
                "Prodamus invoice created: payment_id=%s url=%s",
                payment_id,
                payment_url[:80],
            )
            return ProdamusInvoice(payment_id=payment_id, payment_url=payment_url)

    except Exception as e:
        logger.error("Ошибка при создании инвойса Prodamus: %s", e)
        return None


def verify_prodamus_signature(body: dict[str, Any], received_sign: str) -> bool:
    """
    Проверяет HMAC-SHA256 подпись вебхука от Prodamus.

    Prodamus отправляет POST с JSON и заголовком `Sign` (HMAC-SHA256).
    Ключ — секретный API-ключ магазина.
    """
    api_key = config.PRODAMUS_API_KEY
    if not api_key:
        return False

    # Prodamus подписывает тело как JSON с отсортированными ключами
    body_without_sign = {k: v for k, v in body.items() if k != "signature"}
    sign_string = json.dumps(
        dict(sorted(body_without_sign.items())),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    expected = hmac.new(
        api_key.encode(), sign_string.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, received_sign)
