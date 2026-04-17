"""
Локальна база користувачів бота (/start) для розсилки та підрахунку «підписників» бота.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

UTC = timezone.utc

_DB_PATH = os.environ.get(
    "BOT_USERS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_users.sqlite3"),
)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init_bot_storage() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                blocked INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                source_chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                delivered_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS broadcast_messages (
                broadcast_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                PRIMARY KEY (broadcast_id, user_id),
                FOREIGN KEY (broadcast_id) REFERENCES broadcasts(id) ON DELETE CASCADE
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_broadcast_messages_bid "
            "ON broadcast_messages(broadcast_id)"
        )
        c.commit()


def upsert_bot_user(user_id: int, username: Optional[str], full_name: Optional[str]) -> None:
    now = datetime.now(UTC).isoformat()
    with _conn() as c:
        row = c.execute("SELECT first_seen FROM bot_users WHERE user_id = ?", (user_id,)).fetchone()
        first = row["first_seen"] if row else now
        c.execute(
            """
            INSERT INTO bot_users (user_id, username, full_name, first_seen, last_seen, blocked)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_seen = excluded.last_seen,
                blocked = 0
            """,
            (user_id, username or "", full_name or "", first, now),
        )
        c.commit()


def mark_bot_user_blocked(user_id: int) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE bot_users SET blocked = 1 WHERE user_id = ?",
            (user_id,),
        )
        c.commit()


def get_broadcast_recipient_ids() -> List[int]:
    with _conn() as c:
        rows = c.execute(
            "SELECT user_id FROM bot_users WHERE blocked = 0 ORDER BY user_id"
        ).fetchall()
    return [int(r["user_id"]) for r in rows]


def get_bot_user_counts() -> dict:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
        blocked = c.execute("SELECT COUNT(*) FROM bot_users WHERE blocked = 1").fetchone()[0]
        active = total - blocked

        def count_since(iso_threshold: str) -> int:
            return c.execute(
                "SELECT COUNT(*) FROM bot_users WHERE first_seen >= ? AND blocked = 0",
                (iso_threshold,),
            ).fetchone()[0]

        new_today = count_since(today.isoformat())
        new_week = count_since(week_ago.isoformat())
        new_month = count_since(month_ago.isoformat())

        active_today = c.execute(
            "SELECT COUNT(*) FROM bot_users WHERE last_seen >= ? AND blocked = 0",
            (today.isoformat(),),
        ).fetchone()[0]
        active_week = c.execute(
            "SELECT COUNT(*) FROM bot_users WHERE last_seen >= ? AND blocked = 0",
            (week_ago.isoformat(),),
        ).fetchone()[0]
        active_month = c.execute(
            "SELECT COUNT(*) FROM bot_users WHERE last_seen >= ? AND blocked = 0",
            (month_ago.isoformat(),),
        ).fetchone()[0]

    return {
        "total": total,
        "blocked": blocked,
        "active": active,
        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,
        "active_today": active_today,
        "active_week": active_week,
        "active_month": active_month,
    }


def create_broadcast(
    admin_id: int, source_chat_id: int, source_message_id: int
) -> int:
    now = datetime.now(UTC).isoformat()
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO broadcasts (
                created_at, admin_id, source_chat_id, source_message_id,
                delivered_count, failed_count
            )
            VALUES (?, ?, ?, ?, 0, 0)
            """,
            (now, admin_id, source_chat_id, source_message_id),
        )
        bid = cur.lastrowid
        c.commit()
    return int(bid)


def add_broadcast_delivery(broadcast_id: int, user_id: int, message_id: int) -> None:
    with _conn() as c:
        c.execute(
            """
            INSERT INTO broadcast_messages (broadcast_id, user_id, message_id)
            VALUES (?, ?, ?)
            """,
            (broadcast_id, user_id, message_id),
        )
        c.commit()


def finalize_broadcast_stats(
    broadcast_id: int, delivered_count: int, failed_count: int
) -> None:
    with _conn() as c:
        c.execute(
            """
            UPDATE broadcasts
            SET delivered_count = ?, failed_count = ?
            WHERE id = ?
            """,
            (delivered_count, failed_count, broadcast_id),
        )
        c.commit()


def count_broadcasts() -> int:
    with _conn() as c:
        row = c.execute("SELECT COUNT(*) FROM broadcasts").fetchone()
    return int(row[0])


def list_broadcasts_page(offset: int, limit: int = 8) -> List[sqlite3.Row]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT id, created_at, admin_id, delivered_count, failed_count
            FROM broadcasts
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return list(rows)


def get_broadcast(broadcast_id: int) -> Optional[sqlite3.Row]:
    with _conn() as c:
        row = c.execute(
            """
            SELECT id, created_at, admin_id, source_chat_id, source_message_id,
                   delivered_count, failed_count
            FROM broadcasts WHERE id = ?
            """,
            (broadcast_id,),
        ).fetchone()
    return row


def get_broadcast_deliveries(broadcast_id: int) -> List[tuple]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT user_id, message_id FROM broadcast_messages
            WHERE broadcast_id = ?
            """,
            (broadcast_id,),
        ).fetchall()
    return [(int(r["user_id"]), int(r["message_id"])) for r in rows]


def delete_broadcast_record(broadcast_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
        c.commit()
