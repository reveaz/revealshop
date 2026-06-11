from typing import Optional

import config
from texts import SEP, screen


def is_admin(uid: Optional[int]) -> bool:
    """Return True if *uid* is listed in ADMIN_IDS."""
    return uid is not None and uid in config.ADMIN_IDS


def calc_kwargs() -> dict:
    """Return config values as kwargs for :func:`utils.build_calculation`."""
    return {
        "threshold": config.COMMISSION_THRESHOLD_CNY,
        "tech_fee": config.LOGISTICS_FEE_RUB,
        "min_kg": config.MIN_WEIGHT_KG,
        "usd_per_kg": config.DELIVERY_USD_PER_KG,
        "kzt_per_rub": config.KZT_PER_RUB,
    }

def calculator_intro() -> str:
    t = int(config.COMMISSION_THRESHOLD_CNY)
    return screen(
        "Калькулятор",
        f"Комиссия <b>5%</b> до {t} ¥ · <b>7%</b> от {t} ¥\n"
        f"Лог. сбор {int(config.LOGISTICS_FEE_RUB)} ₽ · "
        f"{config.DELIVERY_USD_PER_KG:.0f}$/кг\n\n"
        "Шаг 1 · сумма товаров в <b>¥</b>:",
    )


ONBOARDING_STEPS = [
    screen("Обучение 1/4", "🛒 <b>Заказ</b>\nТип груза → вес → города → телефон"),
    screen("Обучение 2/4", "🧮 <b>Расчёт</b>\nЦена до оформления"),
    screen("Обучение 3/4", "💱 <b>Курс</b>\nCNY / USD по ЦБ"),
    screen("Обучение 4/4", "📋 <b>Заказы</b>\nСтатусы и трек-код"),
]

