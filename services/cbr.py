import logging
from datetime import datetime

import aiohttp

import config

logger = logging.getLogger(__name__)

_cny_rate: float = config.CNY_RATE
_usd_rate: float = config.USD_RATE
_updated_at: datetime | None = None
_cbr_date: str | None = None
_live: bool = False

CBR_JSON_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
CBR_XML_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


def get_cny_rate() -> float:
    return _cny_rate


def get_usd_rate() -> float:
    return _usd_rate


def get_updated_at() -> datetime | None:
    return _updated_at


def get_cbr_date() -> str | None:
    return _cbr_date


def is_live() -> bool:
    return _live


def _apply_rates(cny: float, usd: float, cbr_date: str | None = None) -> None:
    global _cny_rate, _usd_rate, _updated_at, _cbr_date, _live
    _cny_rate = round(cny, 4)
    _usd_rate = round(usd, 4)
    _cbr_date = cbr_date
    _updated_at = datetime.now()
    _live = True
    config.CNY_RATE = _cny_rate
    config.USD_RATE = _usd_rate


def _parse_valute(item: dict) -> float:
    return round(float(item["Value"]) / float(item.get("Nominal", 1)), 4)


async def _fetch_json(session: aiohttp.ClientSession) -> bool:
    async with session.get(CBR_JSON_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status != 200:
            return False
        data = await resp.json(content_type=None)
    valutes = data.get("Valute", {})
    cny_item = valutes.get("CNY")
    usd_item = valutes.get("USD")
    if not cny_item or not usd_item:
        return False
    cbr_date = data.get("Date")
    if cbr_date:
        cbr_date = cbr_date[:10]
    _apply_rates(_parse_valute(cny_item), _parse_valute(usd_item), cbr_date)
    return True


async def _fetch_xml(session: aiohttp.ClientSession) -> bool:
    import xml.etree.ElementTree as ET

    async with session.get(CBR_XML_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status != 200:
            return False
        raw = await resp.read()
    root = ET.fromstring(raw)
    cbr_date = root.attrib.get("Date")
    rates: dict[str, float] = {}
    for valute in root.findall("Valute"):
        code = valute.findtext("CharCode")
        if code not in ("CNY", "USD"):
            continue
        value = float(valute.findtext("Value", "0").replace(",", "."))
        nominal = float(valute.findtext("Nominal", "1"))
        rates[code] = round(value / nominal, 4)
    if "CNY" not in rates or "USD" not in rates:
        return False
    _apply_rates(rates["CNY"], rates["USD"], cbr_date)
    return True


async def refresh_rates() -> bool:
    global _live
    headers = {"User-Agent": "RevealLorderBot/1.0"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            if await _fetch_json(session):
                logger.info("CBR rates from JSON: CNY=%s USD=%s", _cny_rate, _usd_rate)
                return True
            logger.warning("CBR JSON failed, trying XML…")
            if await _fetch_xml(session):
                logger.info("CBR rates from XML: CNY=%s USD=%s", _cny_rate, _usd_rate)
                return True
    except Exception as exc:
        logger.warning("CBR rates fetch failed: %s", exc)
    _live = False
    return False
