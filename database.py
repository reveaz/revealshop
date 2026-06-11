from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).parent / "bot.db"
DEFAULT_STATUS = "В обработке"

ORDER_STATUSES = [
    "В обработке",
    "В очереди",
    "Расчёт отправлен",
    "Ожидает оплаты",
    "Выкуплен",
    "На складе в Китае",
    "Отправлен",
    "В Астане",
    "Передан в ТК",
    "Доставлен",
    "Отменён",
]

DONE_STATUSES = ("Доставлен", "Отменён")

STATUS_SHORT = {
    "В обработке": "Обработка",
    "В очереди": "Очередь",
    "Расчёт отправлен": "Расчёт",
    "Ожидает оплаты": "Оплата",
    "Выкуплен": "Выкуп",
    "На складе в Китае": "Склад 🇨🇳",
    "Отправлен": "В пути",
    "В Астане": "Астана",
    "Передан в ТК": "ТК",
    "Доставлен": "Готово",
    "Отменён": "Отмена",
}

STATUS_EMOJI = {
    "В обработке": "🔄",
    "В очереди": "⏳",
    "Расчёт отправлен": "🧮",
    "Ожидает оплаты": "💳",
    "Выкуплен": "✅",
    "На складе в Китае": "📦",
    "Отправлен": "🚛",
    "В Астане": "🏙",
    "Передан в ТК": "🚚",
    "Доставлен": "🎉",
    "Отменён": "❌",
}


def order_button_label(order_id: int, status: str) -> str:
    icon = STATUS_EMOJI.get(status, "📦")
    short = STATUS_SHORT.get(status, status[:10])
    return f"{icon} #{order_id} · {short}"


def status_index(status: str) -> int:
    try:
        return ORDER_STATUSES.index(status)
    except ValueError:
        return 0


def status_step_label(status: str) -> str:
    try:
        idx = ORDER_STATUSES.index(status)
    except ValueError:
        return "—"
    return f"{idx + 1}/{len(ORDER_STATUSES)}"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_links TEXT NOT NULL DEFAULT '',
                cost_cny REAL NOT NULL DEFAULT 0,
                weight REAL NOT NULL DEFAULT 0,
                city TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                track_code TEXT NOT NULL DEFAULT '',
                cargo_type TEXT NOT NULL DEFAULT '',
                city_from TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                notify_orders INTEGER NOT NULL DEFAULT 1,
                onboarding_done INTEGER NOT NULL DEFAULT 0,
                balance_discount REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                order_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'KZT',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await _migrate(db)
        await db.commit()


async def _migrate(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in await cursor.fetchall()}
    if user_cols and "notify_orders" not in user_cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN notify_orders INTEGER NOT NULL DEFAULT 1"
        )
    if user_cols and "onboarding_done" not in user_cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN onboarding_done INTEGER NOT NULL DEFAULT 0"
        )
    if user_cols and "balance_discount" not in user_cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN balance_discount REAL NOT NULL DEFAULT 0"
        )

    cursor = await db.execute("PRAGMA table_info(orders)")
    order_cols = {row[1] for row in await cursor.fetchall()}
    if order_cols and "comment" not in order_cols:
        await db.execute(
            "ALTER TABLE orders ADD COLUMN comment TEXT NOT NULL DEFAULT ''"
        )
    if order_cols and "track_code" not in order_cols:
        await db.execute(
            "ALTER TABLE orders ADD COLUMN track_code TEXT NOT NULL DEFAULT ''"
        )
    if order_cols and "cargo_type" not in order_cols:
        await db.execute(
            "ALTER TABLE orders ADD COLUMN cargo_type TEXT NOT NULL DEFAULT ''"
        )
    if order_cols and "city_from" not in order_cols:
        await db.execute(
            "ALTER TABLE orders ADD COLUMN city_from TEXT NOT NULL DEFAULT ''"
        )
    if order_cols and "phone" not in order_cols:
        await db.execute(
            "ALTER TABLE orders ADD COLUMN phone TEXT NOT NULL DEFAULT ''"
        )

    if order_cols and "cargo_type" in order_cols and "product_links" not in order_cols:
        await db.execute("ALTER TABLE orders RENAME TO orders_legacy")
        await db.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_links TEXT NOT NULL,
                cost_cny REAL NOT NULL,
                weight REAL NOT NULL,
                city TEXT NOT NULL,
                status TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.execute(
            """
            INSERT INTO orders (
                id, user_id, product_links, cost_cny, weight, city, status, created_at
            )
            SELECT id, user_id, cargo_type, 0, weight, city, status, created_at
            FROM orders_legacy
            """
        )
        await db.execute("DROP TABLE orders_legacy")


async def upsert_user(user_id: int, username: str | None, full_name: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
            """,
            (user_id, username, full_name),
        )
        await db.commit()


async def get_user(user_id: int) -> aiosqlite.Row | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def set_notify(user_id: int, enabled: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET notify_orders = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id),
        )
        await db.commit()


async def set_onboarding_done(user_id: int, done: bool = True) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET onboarding_done = ? WHERE user_id = ?",
            (1 if done else 0, user_id),
        )
        await db.commit()


async def add_discount(user_id: int, amount: float) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance_discount = balance_discount + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def get_discount(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance_discount FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0.0


async def reset_discount(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance_discount = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def add_notification(user_id: int, message: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
            (user_id, message)
        )
        await db.commit()


async def get_notifications(user_id: int, limit: int = 5) -> list[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        return await cursor.fetchall()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def create_order(
    user_id: int,
    *,
    cargo_type: str = "",
    weight: float = 0,
    city_from: str = "",
    city: str = "",
    phone: str = "",
    product_links: str = "",
    cost_cny: float = 0,
    status: str = DEFAULT_STATUS,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders (
                user_id, cargo_type, weight, city_from, city, phone,
                product_links, cost_cny, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, cargo_type, weight, city_from, city, phone,
             product_links, cost_cny, status),
        )
        await db.commit()
        return cursor.lastrowid


async def get_orders_by_user(user_id: int) -> list[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, product_links, cost_cny, weight, city, status, comment,
                   track_code, cargo_type, city_from, phone, created_at
            FROM orders WHERE user_id = ? ORDER BY id DESC
            """,
            (user_id,),
        )
        return await cursor.fetchall()


async def get_order(order_id: int) -> aiosqlite.Row | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cursor.fetchone()


async def get_order_for_user(order_id: int, user_id: int) -> aiosqlite.Row | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?",
            (order_id, user_id),
        )
        return await cursor.fetchone()


async def set_order_comment(order_id: int, user_id: int, comment: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE orders SET comment = ?
            WHERE id = ? AND user_id = ?
            """,
            (comment, order_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def set_order_track_code(order_id: int, track_code: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE orders SET track_code = ? WHERE id = ?",
            (track_code, order_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_order_track_code(order_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT track_code FROM orders WHERE id = ?", (order_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else ""


async def update_order_status(order_id: int, status: str) -> aiosqlite.Row | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cursor.fetchone()


async def get_recent_orders(limit: int = 20) -> list[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT o.*, u.username, u.full_name
            FROM orders o
            LEFT JOIN users u ON u.user_id = o.user_id
            ORDER BY o.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def count_orders() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM orders")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_trackable_orders() -> list[aiosqlite.Row]:
    """Get all orders with track_code that are not in terminal statuses."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM orders
            WHERE track_code != ''
              AND status NOT IN (?, ?)
            ORDER BY id DESC
            """,
            DONE_STATUSES,
        )
        return await cursor.fetchall()


async def count_pending_orders() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM orders
            WHERE status NOT IN (?, ?)
            """,
            DONE_STATUSES,
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def delete_order(order_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        await db.commit()
        return cursor.rowcount > 0


async def record_payment(
    payment_id: str, order_id: int, amount: float, currency: str = "KZT"
) -> None:
    """Save a new payment record (status='pending' by default)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO payments (payment_id, order_id, amount, currency)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(payment_id) DO UPDATE SET
                order_id = excluded.order_id,
                amount   = excluded.amount,
                currency = excluded.currency
            """,
            (payment_id, order_id, amount, currency),
        )
        await db.commit()


async def update_payment_status(payment_id: str, status: str) -> bool:
    """Update payment status ('pending' -> 'paid' / 'failed')."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE payments SET status = ? WHERE payment_id = ?",
            (status, payment_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_payment(payment_id: str) -> aiosqlite.Row | None:
    """Get payment row by payment_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
        )
        return await cursor.fetchone()


async def get_payment_by_order(order_id: int) -> aiosqlite.Row | None:
    """Get the latest payment for a given order."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM payments WHERE order_id = ? ORDER BY created_at DESC LIMIT 1",
            (order_id,),
        )
        return await cursor.fetchone()
