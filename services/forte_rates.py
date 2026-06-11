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
    rub_buy: float = 0.0
    rub_sell: float = 0.0
    cny_buy: float = 0.0
    cny_sell: float = 0.0
    usd_buy: float = 0.0
    usd_sell: float = 0.0
    updated_at: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        return time.time() - self.updated_at

    def __str__(self) -> str:
        return (
            f"💱 Курсы (ForteBusiness)\n"
            f"   RUB Покупка:  {self.rub_buy:.2f} ₸ | Продажа: {self.rub_sell:.2f} ₸\n"
            f"   CNY Покупка:  {self.cny_buy:.2f} ₸ | Продажа: {self.cny_sell:.2f} ₸\n"
            f"   USD Покупка:  {self.usd_buy:.2f} ₸ | Продажа: {self.usd_sell:.2f} ₸"
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
            try:
                await page.goto(
                    "https://business.forte.kz/profitable-course",
                    wait_until="domcontentloaded",
                    timeout=15_000,
                )
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Timeout goto (ignored): {e}")

            # Если перехватили API — парсим напрямую
            if api_response_data.get("rates"):
                res = _parse_api_response(api_response_data["rates"])
                if res:
                    await browser.close()
                    return res

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
        rates_obj = Rates()
        
        def extract(entry):
            b = float(entry.get("buy") or entry.get("purchase") or entry.get("buyRate", 0))
            s = float(entry.get("sell") or entry.get("sale") or entry.get("sellRate", 0))
            return b, s

        if isinstance(data, dict):
            for code, entry in data.items():
                if not isinstance(entry, dict): continue
                b, s = extract(entry)
                if code.upper() in ("RUB", "RUR"):
                    rates_obj.rub_buy, rates_obj.rub_sell = b, s
                elif code.upper() == "CNY":
                    rates_obj.cny_buy, rates_obj.cny_sell = b, s
                elif code.upper() == "USD":
                    rates_obj.usd_buy, rates_obj.usd_sell = b, s
                    
        elif isinstance(data, list):
            for item in data:
                code = str(item.get("code") or item.get("currency") or "").upper()
                b, s = extract(item)
                if code in ("RUB", "RUR"):
                    rates_obj.rub_buy, rates_obj.rub_sell = b, s
                elif code == "CNY":
                    rates_obj.cny_buy, rates_obj.cny_sell = b, s
                elif code == "USD":
                    rates_obj.usd_buy, rates_obj.usd_sell = b, s

        if rates_obj.rub_buy and rates_obj.cny_buy and rates_obj.usd_buy:
            return rates_obj
        if rates_obj.rub_buy:
            # Fallback if only RUB found
            return rates_obj
            
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

        rates_obj = Rates()
        
        # Ищем паттерн: RUB с двумя числами рядом
        pattern = re.compile(r"RUB[^\d]*(\d+[.,]\d+)[^\d]*(\d+[.,]\d+)", re.IGNORECASE)
        match = pattern.search(text)
        pattern2 = re.compile(r"(?:рубль|рублей|рубл)[^\d]*(\d+[.,]\d+)[^\d]*(\d+[.,]\d+)", re.IGNORECASE)
        match2 = pattern2.search(text)
        
        if match or match2:
            rates_obj.rub_buy = float((match or match2).group(1).replace(",", "."))
            rates_obj.rub_sell = float((match or match2).group(2).replace(",", "."))
        else:
            logger.warning("Курс RUB не найден в HTML")
            return None

        # Ищем USD
        usd_match = re.compile(r"USD[^\d]*(\d+[.,]\d+)[^\d]*(\d+[.,]\d+)", re.IGNORECASE).search(text)
        if usd_match:
            rates_obj.usd_buy = float(usd_match.group(1).replace(",", "."))
            rates_obj.usd_sell = float(usd_match.group(2).replace(",", "."))

        # Ищем CNY
        cny_match = re.compile(r"CNY[^\d]*(\d+[.,]\d+)[^\d]*(\d+[.,]\d+)", re.IGNORECASE).search(text)
        if cny_match:
            rates_obj.cny_buy = float(cny_match.group(1).replace(",", "."))
            rates_obj.cny_sell = float(cny_match.group(2).replace(",", "."))

        return rates_obj

    except Exception as e:
        logger.error(f"Ошибка парсинга HTML: {e}")
        return None


# ──────────────────────────────────────────────
# Глобальный экземпляр кеша (импортировать в бот)
# ──────────────────────────────────────────────

rates_cache = RatesCache(ttl=1800)   # обновляется раз в 30 минут
