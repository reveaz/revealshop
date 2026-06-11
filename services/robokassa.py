"""
services/robokassa.py
====================
Адаптер для платежного шлюза Robokassa.

Документация API:       https://docs.robokassa.ru/
Фискализация (ФФД 1.2): https://docs.robokassa.ru/fiscalization/

Подпись при создании платежа (Password1):
    MD5(MerchantLogin:OutSum:InvId:Receipt:Password1)

Подпись при ResultURL (Password2):
    MD5(OutSum:InvId:Password2)
"""

import hashlib
import json
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any

import config

logger = logging.getLogger(__name__)

_BASE_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


# ── Датаклассы ──────────────────────────────────────────────


@dataclass
class ReceiptItem:
    """Позиция в фискальном чеке (ФФД 1.2).

    Критически важно: `name` должен содержать конкретное наименование
    товара (бренд + тип), а НЕ обобщённое «Оплата заказа».
    Robokassa / ФНС отклонят чек с пустой или абстрактной корзиной.
    """

    name: str  # «Кроссовки Nike Air Max, зак. #42»
    quantity: int = 1
    sum: float = 0.0
    payment_method: str = "full_payment"
    payment_object: str = "commodity"
    tax: str = "none"  # none | vat0 | vat10 | vat20


@dataclass
class RobokassaInvoice:
    """Результат генерации платёжной ссылки."""

    inv_id: int  # InvId = order_id
    payment_url: str


# ── Вспомогательные функции ─────────────────────────────────


def _sign(*parts: str, algo: str = "md5") -> str:
    """Собирает строку `part1:part2:…` и хеширует MD5 или SHA256."""
    raw = ":".join(parts)
    if algo == "sha256":
        return hashlib.sha256(raw.encode()).hexdigest()
    return hashlib.md5(raw.encode()).hexdigest()


def _build_receipt_json(items: list[ReceiptItem]) -> str:
    """Формирует JSON чека для фискализации (ФФД 1.2)."""
    sno = getattr(config, "ROBOKASSA_SNO", "usn_income")
    receipt: dict[str, Any] = {
        "sno": sno,
        "items": [
            {
                "name": it.name,
                "quantity": it.quantity,
                "sum": round(it.sum, 2),
                "payment_method": it.payment_method,
                "payment_object": it.payment_object,
                "tax": it.tax,
            }
            for it in items
        ],
    }
    return json.dumps(receipt, ensure_ascii=False, separators=(",", ":"))


# ── Публичный API ───────────────────────────────────────────


def robokassa_payment_url(
    inv_id: int,
    out_sum: float,
    description: str,
    items: list[ReceiptItem],
) -> RobokassaInvoice | None:
    """
    Генерирует URL для оплаты через Robokassa.

    :param inv_id:      ID заказа (используется как InvId).
    :param out_sum:     Сумма к оплате (RUB).
    :param description: Описание платежа (для страницы оплаты).
    :param items:       Список позиций для фискального чека.
    :return:            RobokassaInvoice или None при ошибке конфигурации.
    """
    login = config.ROBOKASSA_LOGIN
    pwd1 = config.ROBOKASSA_PASSWORD1
    if not login or not pwd1:
        logger.error("ROBOKASSA_LOGIN / ROBOKASSA_PASSWORD1 не заданы в .env")
        return None

    algo = getattr(config, "ROBOKASSA_HASH_ALGO", "md5")
    out_sum_str = f"{out_sum:.2f}"

    receipt_json = _build_receipt_json(items)
    receipt_encoded = urllib.parse.quote(receipt_json)

    # Подпись: MerchantLogin:OutSum:InvId:Receipt:Password1
    sig = _sign(login, out_sum_str, str(inv_id), receipt_encoded, pwd1, algo=algo)

    params = {
        "MerchantLogin": login,
        "OutSum": out_sum_str,
        "InvId": str(inv_id),
        "Description": description,
        "SignatureValue": sig,
        "Receipt": receipt_encoded,
        "Encoding": "utf-8",
    }
    if getattr(config, "ROBOKASSA_IS_TEST", False):
        params["IsTest"] = "1"

    url = f"{_BASE_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"

    logger.info("Robokassa URL: InvId=%s sum=%s", inv_id, out_sum_str)
    return RobokassaInvoice(inv_id=inv_id, payment_url=url)


def verify_result_signature(out_sum: str, inv_id: str, received_sign: str) -> bool:
    """
    Проверяет подпись ResultURL от Robokassa.
    Формула: MD5(OutSum:InvId:Password2)
    """
    pwd2 = config.ROBOKASSA_PASSWORD2
    if not pwd2:
        return False

    algo = getattr(config, "ROBOKASSA_HASH_ALGO", "md5")
    expected = _sign(out_sum, inv_id, pwd2, algo=algo)
    return expected.lower() == received_sign.lower()
