"""
forte_rates.py
==============
Парсер курсов валют с ForteBusiness + кеш.

Зависимости:
    pip install playwright httpx beautifulsoup4
    playwright install chromium
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Структура данных
# ──────────────────────────────────────────────

@dataclass
class Rates:
    buy: float
    sell: float
    currency: str = "RUB"          # валюта которую парсим (RUB/KZT по умолчанию)
    updated_at: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        return time.time() - self.updated_at

    def __str__(self) -> str:
        return (
            f"💱 Курс RUB/KZT (ForteBusiness)\n"
            f"   Покупка:  {self.buy:.2f} ₸\n"
            f"   Продажа:  {self.sell:.2f} ₸"
        )


# ──────────────────────────────────────────────
# Кеш (живёт TTL секунд)
# ──────────────────────────────────────────────

class RatesCache:
    def __init__(self, ttl: int = 1800):   # 30 минут по умолчанию
        self._ttl = ttl
        self._rates: Optional[Rates] = None
        self._lock = asyncio.Lock()

    def is_fresh(self) -> bool:
        return self._rates is not None and self._rates.age_seconds() < self._ttl

    async def get(self) -> Optional[Rates]:
        async with self._lock:
            if not self.is_fresh():
                self._rates = await fetch_rates()
            return self._rates

    async def force_refresh(self) -> Optional[Rates]:
        async with self._lock:
            self._rates = await fetch_rates()
            return self._rates


# ──────────────────────────────────────────────
# Парсер
# ──────────────────────────────────────────────

async def fetch_rates() -> Optional[Rates]:
    """
    Получает курс RUB с business.forte.kz через Playwright.
    Сайт — Next.js SPA, данные грузятся динамически, поэтому
    нужен headless-браузер.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Перехватываем ответы от API внутри сайта
            api_response_data = {}

            async def handle_response(response):
                url = response.url
                # Ищем XHR/fetch запросы с курсами
                if "rate" in url.lower() or "currency" in url.lower() or "exchange" in url.lower():
                    try:
                        data = await response.json()
                        api_response_data["rates"] = data
                        logger.debug(f"Перехвачен API ответ: {url}")
                    except Exception:
                        pass

            page.on("response", handle_response)

            # Открываем страницу с курсами
            await page.goto(
                "https://business.forte.kz/profitable-course",
                wait_until="networkidle",
                timeout=30_000,
            )

            # Если перехватили API — парсим напрямую
            if api_response_data.get("rates"):
                return _parse_api_response(api_response_data["rates"])

            # Иначе парсим HTML
            content = await page.content()
            await browser.close()

            return _parse_html(content)

    except Exception as e:
        logger.error(f"Ошибка при получении курса: {e}")
        return None


def _parse_api_response(data: dict) -> Optional[Rates]:
    """Парсит JSON ответ от внутреннего API Forte (структура может меняться)."""
    try:
        # Попробуем несколько вариантов структуры
        for key in ["RUB", "rub", "RUR", "rur"]:
            if key in data:
                entry = data[key]
                if isinstance(entry, dict):
                    buy = float(entry.get("buy") or entry.get("purchase") or entry.get("buyRate", 0))
                    sell = float(entry.get("sell") or entry.get("sale") or entry.get("sellRate", 0))
                    if buy and sell:
                        return Rates(buy=buy, sell=sell)

        # Если данные в списке
        if isinstance(data, list):
            for item in data:
                code = str(item.get("code") or item.get("currency") or "").upper()
                if code in ("RUB", "RUR"):
                    buy = float(item.get("buy") or item.get("purchase") or 0)
                    sell = float(item.get("sell") or item.get("sale") or 0)
                    if buy and sell:
                        return Rates(buy=buy, sell=sell)

        return None
    except Exception as e:
        logger.error(f"Ошибка парсинга API ответа: {e}")
        return None


def _parse_html(html: str) -> Optional[Rates]:
    """Парсит отрендеренный HTML страницы Forte Business."""
    from bs4 import BeautifulSoup
    import re

    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        # Ищем паттерн: RUB с двумя числами рядом
        pattern = re.compile(
            r"RUB[^\d]*(\d+[.,]\d+)[^\d]*(\d+[.,]\d+)",
            re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            buy = float(match.group(1).replace(",", "."))
            sell = float(match.group(2).replace(",", "."))
            return Rates(buy=buy, sell=sell)

        # Альтернативный паттерн — ищем «Рубль» или «рубль»
        pattern2 = re.compile(
            r"(?:рубль|рублей|рубл)[^\d]*(\d+[.,]\d+)[^\d]*(\d+[.,]\d+)",
            re.IGNORECASE
        )
        match2 = pattern2.search(text)
        if match2:
            buy = float(match2.group(1).replace(",", "."))
            sell = float(match2.group(2).replace(",", "."))
            return Rates(buy=buy, sell=sell)

        logger.warning("Курс RUB не найден в HTML")
        return None

    except Exception as e:
        logger.error(f"Ошибка парсинга HTML: {e}")
        return None


# ──────────────────────────────────────────────
# Глобальный экземпляр кеша (импортировать в бот)
# ──────────────────────────────────────────────

rates_cache = RatesCache(ttl=1800)   # обновляется раз в 30 минут
