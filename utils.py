import re

import database as db
from texts import SEP, progress_bar, screen

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def parse_number(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text)


def commission_percent(cost_cny: float, threshold_cny: float) -> float:
    return 5.0 if cost_cny < threshold_cny else 7.0


def estimate_weight(category: str) -> float:
    """Возвращает примерный вес (кг) по категории из справочника."""
    import config
    return config.CATEGORY_WEIGHTS.get(category.lower().strip(), config.CATEGORY_WEIGHTS["другое"])


def delivery_usd(weight_kg: float, min_kg: float, usd_per_kg: float) -> float:
    if weight_kg <= 0:
        return 0.0
    return round(max(weight_kg, min_kg) * usd_per_kg, 2)


def build_calculation(
    cost_cny: float,
    weight_kg: float = 0.0,
    *,
    category: str = "",
    discount: float = 0.0,
    cny_rate: float | None = None,
    usd_rate: float | None = None,
    threshold: float,
    tech_fee: float,
    min_kg: float,
    usd_per_kg: float,
    kzt_per_rub: float,
) -> dict:
    """Расчёт стоимости заказа.

    Если передан `category` и `weight_kg == 0`, вес берётся из справочника
    CATEGORY_WEIGHTS (модель «единый чекаут»). Если передан `weight_kg > 0`,
    используется точное значение (обратная совместимость с калькулятором).

    `discount` — баланс скидок пользователя (вычитается из итога).
    """
    import config
    import math

    cny = cny_rate if cny_rate is not None else config.CNY_RATE
    usd = usd_rate if usd_rate is not None else config.USD_RATE

    # Определяем вес: точный или из справочника
    if weight_kg > 0:
        effective_weight = weight_kg
    elif category:
        effective_weight = estimate_weight(category)
    else:
        effective_weight = 0.0

    # Add 3% to original cost in CNY as requested
    cost_cny_with_fee = cost_cny * 1.03

    # Округляем в пользу мерчанта (ceil)
    goods_rub = math.ceil(cost_cny_with_fee * cny)
    
    # Порог комиссии проверяем по ИСХОДНОЙ сумме до наценки 3%
    pct = commission_percent(cost_cny, threshold)
    commission_rub = math.ceil(goods_rub * pct / 100)
    
    del_usd = delivery_usd(effective_weight, min_kg, usd_per_kg)
    delivery_rub = math.ceil(del_usd * usd)

    # Итог: товар + комиссия + логистика + сбор
    subtotal_rub = goods_rub + commission_rub + delivery_rub + math.ceil(tech_fee)

    # Вычитаем скидку (баланс пользователя), не уходя в минус
    applied_discount = min(discount, subtotal_rub) if discount > 0 else 0.0
    total_rub = math.ceil(subtotal_rub - applied_discount)

    return {
        "cny_rate": cny,
        "usd_rate": usd,
        "goods_rub": float(goods_rub),
        "commission_pct": pct,
        "commission_rub": float(commission_rub),
        "delivery_usd": del_usd,
        "delivery_rub": float(delivery_rub),
        "estimated_weight": effective_weight,
        "subtotal_rub": float(subtotal_rub),
        "discount_applied": float(applied_discount),
        "total_rub": float(total_rub),
        "total_kzt": math.ceil(total_rub * kzt_per_rub),
    }


def fmt_money(value: float) -> str:
    return f"{value:,.2f} ₽".replace(",", " ")


def fmt_calc_result_body(data: dict) -> str:
    if data['delivery_usd'] > 0:
        del_line = f"├ доставка … {data['delivery_usd']}$ ({fmt_money(data['delivery_rub'])})"
    else:
        del_line = "├ доставка … точная сумма после взвешивания"

    lines = [
        f"├ товар …… {fmt_money(data['goods_rub'])}",
        f"├ комиссия {data['commission_pct']:.0f}% … {fmt_money(data['commission_rub'])}",
        del_line,
        f"└ <b>итого … {fmt_money(data['total_rub'])}</b>  ·  {data['total_kzt']:,} ₸".replace(",", " ")
    ]
    return "\n".join(lines)


def fmt_calc_result(data: dict) -> str:
    body = f"<b>📦 Обычный</b>\n{fmt_calc_result_body(data)}"
    return screen("Результат", body)


async def format_rate_message() -> str:
    from config import now_astana, now_msk
    import config

    msk = now_msk().strftime("%H:%M")
    ast = now_astana().strftime("%H:%M")

    forte_text = (
        "💱 <b>Курс (настроен вручную)</b>\n"
        f"   🇨🇳 <b>CNY</b> ~ {config.CNY_RATE:.4f} ₽\n"
        f"   🇺🇸 <b>USD</b> ~ {config.USD_RATE:.4f} ₽\n\n"
    )

    return screen(
        "Курс валют",
        f"{forte_text}"
        f"🕐 Астана {ast} · МСК {msk}",
    )


def format_order_detail(row) -> str:
    keys = row.keys() if hasattr(row, "keys") else []
    comment = row["comment"] or "—"
    status = row["status"]
    icon = db.STATUS_EMOJI.get(status, "📦")
    idx = db.status_index(status)
    bar = progress_bar(idx + 1, len(db.ORDER_STATUSES))
    step = db.status_step_label(status)

    track = row["track_code"] if "track_code" in keys else ""
    track_line = f"📍 Трек: <code>{track}</code>\n" if track else ""

    cargo_type = row["cargo_type"] if "cargo_type" in keys else ""
    city_from = row["city_from"] if "city_from" in keys else ""
    phone = row["phone"] if "phone" in keys else ""

    if cargo_type:
        weight_str = f"  ·  ⚖️ {row['weight']} кг" if row['weight'] and float(row['weight']) > 0 else ""
        info_lines = f"📦 {cargo_type}{weight_str}\n"
        if city_from:
            info_lines += f"📍 {city_from} → {row['city']}\n"
        else:
            info_lines += f"📍 {row['city']}\n"
        if phone:
            info_lines += f"📞 {phone}\n"
    else:
        links_raw = row["product_links"] or ""
        links = [l for l in links_raw.split("\n") if l.strip()]
        if links:
            first = links[0][:50] + ("…" if len(links[0]) > 50 else "")
            more = f"  <i>+{len(links) - 1} ссылок</i>" if len(links) > 1 else ""
            info_lines = (
                f"💰 {row['cost_cny']} ¥  ·  ⚖️ {row['weight']} кг\n"
                f"📍 {row['city']}\n"
                f"🔗 {first}{more}\n"
            )
        else:
            info_lines = (
                f"⚖️ {row['weight']} кг\n"
                f"📍 {row['city']}\n"
            )

    return (
        f"{icon} <b>Заказ #{row['id']}</b>\n"
        f"{bar}  <i>{step}</i>\n"
        f"{SEP}\n"
        f"📌 <b>{status}</b>\n"
        f"{track_line}\n"
        f"{info_lines}"
        f"💬 {comment}\n"
        f"<i>{row['created_at']}</i>"
    )

