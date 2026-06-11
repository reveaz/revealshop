import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

TRACKER_DIR = Path(__file__).resolve().parent.parent / "tracker"
TRACKER_SCRIPT = TRACKER_DIR / "src" / "main.js"

STATUS_PATTERNS = {
    "Доставлен": ("Delivered", "✅"),
    "В пути": ("InTransit", "🚚"),
    "Готов к выдаче": ("AvailableForPickup", "📬"),
    "Выдан курьеру": ("OutForDelivery", "🛵"),
    "Информация получена": ("InfoReceived", "📋"),
    "Попытка доставки": ("AttemptFail", "⚠️"),
    "Исключение": ("Exception", "❌"),
    "Возвращён": ("Returned", "↩️"),
    "Истёк срок": ("Expired", "⏰"),
    "Не найден": ("NotFound", "❓"),
}

_STATUS_LINE_RE = re.compile(
    r"(?:Статус посылки|Статус|Status)[:\s]*(.+)",
    re.IGNORECASE,
)


@dataclass
class TrackingResult:
    number: str
    status: str
    status_ru: str
    emoji: str
    latest_event: str
    raw_text: str


def _parse_output(track_number: str, raw: str) -> TrackingResult | None:
    if not raw.strip():
        return None

    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]

    status_ru = ""
    emoji = "📦"
    status_en = "Unknown"

    for line in lines:
        m = _STATUS_LINE_RE.search(line)
        if m:
            status_ru = m.group(1).strip()
            break

    if not status_ru:
        for line in lines:
            for pattern_ru in STATUS_PATTERNS:
                if pattern_ru.lower() in line.lower():
                    status_ru = pattern_ru
                    break
            if status_ru:
                break

    if status_ru:
        for pattern_ru, (en, em) in STATUS_PATTERNS.items():
            if pattern_ru.lower() in status_ru.lower():
                status_en = en
                emoji = em
                break

    event_lines = []
    skip_prefixes = ("Номер", "Статус", "Status", "Number")
    for line in lines:
        if any(line.startswith(p) for p in skip_prefixes):
            continue
        event_lines.append(line)

    latest_event = event_lines[0] if event_lines else raw.strip()[:200]

    return TrackingResult(
        number=track_number,
        status=status_en,
        status_ru=status_ru or "—",
        emoji=emoji,
        latest_event=latest_event,
        raw_text=raw.strip(),
    )


async def get_tracking_info(track_number: str) -> TrackingResult | None:
    if not TRACKER_SCRIPT.exists():
        logger.error("Tracker script not found: %s", TRACKER_SCRIPT)
        return None

    cmd = ["node", str(TRACKER_SCRIPT), track_number]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(TRACKER_DIR),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        logger.warning("Tracker script timed out for %s", track_number)
        try:
            proc.kill()
        except Exception:
            pass
        return None
    except Exception as exc:
        logger.warning("Tracker script error: %s", exc)
        return None

    output = stdout.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        logger.warning(
            "Tracker exit code %s for %s: %s",
            proc.returncode,
            track_number,
            err[:300],
        )
        if output:
            return _parse_output(track_number, output)
        return None

    return _parse_output(track_number, output)


# Mapping from 17track status keywords to bot ORDER_STATUSES.
# The tracker returns status_ru like "В пути", "Доставлен", etc.
# We map them to internal order statuses.
TRACK_TO_ORDER_STATUS: dict[str, str] = {
    # status_en from _parse_output → order status
    "InfoReceived": "На складе в Китае",
    "InTransit": "Отправлен",
    "AvailableForPickup": "В Астане",
    "OutForDelivery": "Передан в ТК",
    "Delivered": "Доставлен",
    "AttemptFail": "Передан в ТК",
    "Exception": "Отправлен",
    "Returned": "Отменён",
}


def map_tracking_to_order_status(result: TrackingResult) -> str | None:
    """Map a TrackingResult to an internal order status, or None if unknown."""
    return TRACK_TO_ORDER_STATUS.get(result.status)

