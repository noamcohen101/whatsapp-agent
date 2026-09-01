"""SQLite conversation memory + message dedup. One connection per call."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DATABASE_PATH, MAX_HISTORY


@contextmanager
def _conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_chat ON conversations(chat_id, id)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
                id_message TEXT PRIMARY KEY,
                seen_at    TEXT NOT NULL
            )
            """
        )


def already_processed(id_message: str) -> bool:
    if not id_message:
        return False
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM processed_messages WHERE id_message = ?", (id_message,)
        ).fetchone()
        if row:
            return True
        c.execute(
            "INSERT INTO processed_messages (id_message, seen_at) VALUES (?, ?)",
            (id_message, datetime.now(timezone.utc).isoformat()),
        )
        return False


def append(chat_id: str, role: str, content: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO conversations (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def tail(chat_id: str, n: int = MAX_HISTORY) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM conversations WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, n),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
