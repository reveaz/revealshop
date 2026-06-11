"""
Background task that periodically checks tracking status for all orders
with a track_code and automatically updates their status.
"""
import asyncio
import logging

from aiogram import Bot

import database as db
from services.tracker import get_tracking_info, map_tracking_to_order_status

logger = logging.getLogger(__name__)

# Check interval in seconds (30 minutes)
CHECK_INTERVAL = 30 * 60

# Delay between individual track checks to avoid rate-limiting (seconds)
PER_TRACK_DELAY = 15


async def check_and_update_order(bot: Bot, order) -> None:
    """Check tracking for a single order and update status if changed."""
    order_id = order["id"]
    track_code = order["track_code"]
    old_status = order["status"]
    user_id = order["user_id"]

    logger.info("Auto-tracking #%s: %s", order_id, track_code)

    result = await get_tracking_info(track_code)
    if result is None:
        logger.warning("Auto-tracking #%s: no result for %s", order_id, track_code)
        return

    new_status = map_tracking_to_order_status(result)
    if new_status is None:
        logger.info(
            "Auto-tracking #%s: unknown status '%s' (%s), skipping",
            order_id, result.status_ru, result.status,
        )
        return

    if new_status == old_status:
        logger.info("Auto-tracking #%s: status unchanged (%s)", order_id, old_status)
        return

    # Check if new status is "forward" compared to old (don't go backward)
    new_idx = db.status_index(new_status)
    old_idx = db.status_index(old_status)
    if new_idx <= old_idx:
        logger.info(
            "Auto-tracking #%s: new status '%s' (%d) not ahead of '%s' (%d), skipping",
            order_id, new_status, new_idx, old_status, old_idx,
        )
        return

    # Update the status
    await db.update_order_status(order_id, new_status)
    logger.info("Auto-tracking #%s: %s → %s", order_id, old_status, new_status)

    # Notify the user
    user = await db.get_user(user_id)
    if user and user["notify_orders"]:
        emoji = db.STATUS_EMOJI.get(new_status, "📦")
        try:
            await bot.send_message(
                user_id,
                f"{emoji} <b>#{order_id}</b> — статус обновлён\n\n"
                f"📌 <b>{new_status}</b>\n"
                f"📍 Трек: <code>{track_code}</code>\n"
                f"📝 {result.latest_event}",
            )
        except Exception as exc:
            logger.warning("Failed to notify user %s: %s", user_id, exc)


async def auto_track_loop(bot: Bot) -> None:
    """Infinite loop that checks all trackable orders periodically."""
    logger.info("Auto-tracking loop started (interval: %ds)", CHECK_INTERVAL)
    while True:
        try:
            orders = await db.get_trackable_orders()
            if orders:
                logger.info("Auto-tracking: %d orders to check", len(orders))
                for order in orders:
                    try:
                        await check_and_update_order(bot, order)
                    except Exception as exc:
                        logger.error(
                            "Auto-tracking error for #%s: %s",
                            order["id"], exc,
                        )
                    await asyncio.sleep(PER_TRACK_DELAY)
            else:
                logger.debug("Auto-tracking: no trackable orders")
        except Exception as exc:
            logger.error("Auto-tracking loop error: %s", exc)

        await asyncio.sleep(CHECK_INTERVAL)


async def check_single_order(bot: Bot, order_id: int) -> str | None:
    """
    Check tracking for a single order immediately.
    Returns the new status if updated, or None.
    Called when admin sets a track code.
    """
    order = await db.get_order(order_id)
    if not order or not order["track_code"]:
        return None

    result = await get_tracking_info(order["track_code"])
    if result is None:
        return None

    new_status = map_tracking_to_order_status(result)
    if new_status is None or new_status == order["status"]:
        return None

    new_idx = db.status_index(new_status)
    old_idx = db.status_index(order["status"])
    if new_idx <= old_idx:
        return None

    await db.update_order_status(order_id, new_status)

    # Notify user
    user = await db.get_user(order["user_id"])
    if user and user["notify_orders"]:
        emoji = db.STATUS_EMOJI.get(new_status, "📦")
        try:
            await bot.send_message(
                order["user_id"],
                f"{emoji} <b>#{order_id}</b> — статус обновлён\n\n"
                f"📌 <b>{new_status}</b>\n"
                f"📍 Трек: <code>{order['track_code']}</code>\n"
                f"📝 {result.latest_event}",
            )
        except Exception:
            pass

    return new_status
