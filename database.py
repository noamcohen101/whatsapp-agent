"""Postgres (Supabase) conversation memory + message dedup. Connection per call."""
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from config import DATABASE_URL, MAX_HISTORY


@contextmanager
def _conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         BIGSERIAL PRIMARY KEY,
                chat_id    TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_chat ON conversations (chat_id, id)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
                id_message TEXT PRIMARY KEY,
                seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id         BIGSERIAL PRIMARY KEY,
                category   TEXT NOT NULL DEFAULT 'general',
                content    TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def add_memory(content: str, category: str = "general") -> int:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO memories (category, content) VALUES (%s, %s) RETURNING id",
            (category, content),
        )
        return cur.fetchone()[0]


def all_memories() -> list[dict]:
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, category, content FROM memories ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def delete_memory(memory_id: int) -> bool:
    with _conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
        return cur.rowcount > 0


def already_processed(id_message: str) -> bool:
    if not id_message:
        return False
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO processed_messages (id_message) VALUES (%s) "
            "ON CONFLICT (id_message) DO NOTHING",
            (id_message,),
        )
        return cur.rowcount == 0


def append(chat_id: str, role: str, content: str) -> None:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (chat_id, role, content) VALUES (%s, %s, %s)",
            (chat_id, role, content),
        )


def tail(chat_id: str, n: int = MAX_HISTORY) -> list[dict]:
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT role, content FROM conversations WHERE chat_id = %s "
            "ORDER BY id DESC LIMIT %s",
            (chat_id, n),
        )
        rows = cur.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
