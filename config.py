import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent
load_dotenv(_ROOT / ".env")

CNY_RATE = float(os.getenv("CNY_RATE", "11.09"))
USD_RATE = float(os.getenv("USD_RATE", "76.62"))
KZT_PER_RUB = float(os.getenv("KZT_PER_RUB", "6.47"))
DELIVERY_USD_PER_KG = float(os.getenv("DELIVERY_USD_PER_KG", "5"))
MIN_WEIGHT_KG = float(os.getenv("MIN_WEIGHT_KG", "1"))
LOGISTICS_FEE_RUB = float(os.getenv("LOGISTICS_FEE_RUB", "500"))
TECH_FEE_RUB = LOGISTICS_FEE_RUB  # backward compat alias
COMMISSION_THRESHOLD_CNY = float(os.getenv("COMMISSION_THRESHOLD_CNY", "1000"))
COMMISSION_THRESHOLD_RUB = float(os.getenv("COMMISSION_THRESHOLD_RUB", "50000"))  # legacy
WORK_HOURS = os.getenv("WORK_HOURS", "13:00 — 22:00 МСК")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Henawn")
NEWS_CHANNEL_URL = os.getenv("NEWS_CHANNEL_URL", "https://t.me/+MExhZmp8kSZmMmRi")
TIKTOK_URL = os.getenv("TIKTOK_URL", "https://www.tiktok.com/@reveallshop")
GUIDE_VIDEO_URL = os.getenv("GUIDE_VIDEO_URL", "")
POLICY_URL = os.getenv("POLICY_URL", "https://telegra.ph/Politika-konfidencialnosti-Reveallshop-06-06")
TERMS_URL = os.getenv("TERMS_URL", "https://telegra.ph/Polzovatelskoe-soglashenie-revealshop-06-06")
MAX_LINKS_PER_ORDER = 10
TRACK17_API_KEY = os.getenv("TRACK17_API_KEY", "")

# Prodamus payment gateway
PRODAMUS_API_URL = os.getenv("PRODAMUS_API_URL", "")   # e.g. https://yourshop.payform.ru
PRODAMUS_API_KEY = os.getenv("PRODAMUS_API_KEY", "")   # secret key
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")           # e.g. https://yourdomain.com
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

# Banners
BANNER_MENU = _ROOT / "assets" / "banner_menu.png"
BANNER_GUIDE = _ROOT / "assets" / "banner_guide.png"

_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()}

_MSK = timezone(timedelta(hours=3))
_ALMATY = timezone(timedelta(hours=5))


def _tz(name: str, fallback: timezone) -> timezone:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        return fallback


def now_msk() -> datetime:
    return datetime.now(_tz("Europe/Moscow", _MSK))


def now_astana() -> datetime:
    return datetime.now(_tz("Asia/Almaty", _ALMATY))
