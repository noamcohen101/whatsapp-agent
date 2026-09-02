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
        cur.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_usage (
                id            BIGSERIAL PRIMARY KEY,
                model         TEXT NOT NULL,
                input_tokens  INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit (
                id         BIGSERIAL PRIMARY KEY,
                actor      TEXT DEFAULT 'bot',
                action     TEXT NOT NULL,
                detail     TEXT DEFAULT '',
                context    TEXT DEFAULT 'private',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id         BIGSERIAL PRIMARY KEY,
                name       TEXT NOT NULL,
                variant_a  TEXT DEFAULT '',
                variant_b  TEXT DEFAULT '',
                metric     TEXT DEFAULT '',
                result_a   TEXT DEFAULT '',
                result_b   TEXT DEFAULT '',
                status     TEXT DEFAULT 'running',
                winner     TEXT DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id         BIGSERIAL PRIMARY KEY,
                decision   TEXT NOT NULL,
                context    TEXT DEFAULT '',
                rationale  TEXT DEFAULT '',
                outcome    TEXT DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id           BIGSERIAL PRIMARY KEY,
                title        TEXT NOT NULL,
                domain       TEXT DEFAULT 'general',
                status       TEXT DEFAULT 'open',
                priority     TEXT DEFAULT 'normal',
                due          TEXT DEFAULT '',
                waiting_on   TEXT DEFAULT '',
                next_action  TEXT DEFAULT '',
                source       TEXT DEFAULT '',
                notes        TEXT DEFAULT '',
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                id              BIGSERIAL PRIMARY KEY,
                order_id        TEXT NOT NULL,
                tracking_number TEXT NOT NULL,
                carrier         TEXT DEFAULT '',
                customer_name   TEXT DEFAULT '',
                customer_phone  TEXT DEFAULT '',
                last_status     TEXT DEFAULT 'new',
                active          BOOLEAN DEFAULT TRUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (tracking_number)
            )
            """
        )


def add_shipment(order_id, tracking_number, carrier, name, phone) -> str:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO shipments (order_id, tracking_number, carrier, customer_name, customer_phone)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (tracking_number) DO UPDATE SET order_id=EXCLUDED.order_id,
                 carrier=EXCLUDED.carrier, active=TRUE, updated_at=NOW()
               RETURNING id""",
            (order_id, tracking_number, carrier, name, phone),
        )
        return str(cur.fetchone()[0])


def active_shipments() -> list[dict]:
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM shipments WHERE active ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def update_shipment_status(shipment_id: int, status: str, deactivate: bool = False) -> None:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "UPDATE shipments SET last_status=%s, active=%s, updated_at=NOW() WHERE id=%s",
            (status, not deactivate, shipment_id),
        )


def task_add(title, domain="general", priority="normal", due="", next_action="",
             waiting_on="", source="", notes="") -> str:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO tasks (title, domain, priority, due, next_action, waiting_on, source, notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (title, domain, priority, due, next_action, waiting_on, source, notes),
        )
        return str(cur.fetchone()[0])


def task_list(status="open", domain="") -> list[dict]:
    q = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status and status != "all":
        q += " AND status = %s"
        params.append(status)
    if domain:
        q += " AND domain = %s"
        params.append(domain)
    q += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, id"
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]


def task_update(task_id: int, **fields) -> bool:
    allowed = {"title", "domain", "status", "priority", "due", "waiting_on", "next_action", "notes"}
    sets = {k: v for k, v in fields.items() if k in allowed and v is not None and v != ""}
    if not sets:
        return False
    cols = ", ".join(f"{k} = %s" for k in sets)
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            f"UPDATE tasks SET {cols}, updated_at = NOW() WHERE id = %s",
            [*sets.values(), task_id],
        )
        return cur.rowcount > 0


def setting_set(key: str, value: str) -> None:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (%s,%s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, value),
        )


def setting_get(key: str, default: str = "") -> str:
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cur.fetchone()
        return row[0] if row else default


def usage_log(model: str, input_tokens: int, output_tokens: int) -> None:
    try:
        with _conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO llm_usage (model, input_tokens, output_tokens) VALUES (%s,%s,%s)",
                (model, input_tokens, output_tokens),
            )
    except Exception as e:  # noqa: BLE001
        print(f"[usage] log failed: {e}")


def usage_since(days: int) -> list[dict]:
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT model, SUM(input_tokens) in_tok, SUM(output_tokens) out_tok, COUNT(*) calls "
            "FROM llm_usage WHERE created_at > NOW() - (%s || ' days')::interval GROUP BY model",
            (days,),
        )
        return [dict(r) for r in cur.fetchall()]


def settings_all() -> dict:
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT key, value FROM settings")
        return dict(cur.fetchall())


def audit_log(action: str, detail: str = "", context: str = "private", actor: str = "bot") -> None:
    try:
        with _conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO audit (actor, action, detail, context) VALUES (%s,%s,%s,%s)",
                (actor, action[:120], detail[:800], context),
            )
    except Exception as e:  # noqa: BLE001 - audit must never break a request
        print(f"[audit] failed: {e}")


def audit_recent(hours: int = 24, limit: int = 60) -> list[dict]:
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT action, detail, context, created_at FROM audit "
            "WHERE created_at > NOW() - (%s || ' hours')::interval "
            "ORDER BY id DESC LIMIT %s",
            (hours, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def experiment_add(name, variant_a, variant_b, metric) -> str:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO experiments (name, variant_a, variant_b, metric) VALUES (%s,%s,%s,%s) RETURNING id",
            (name, variant_a, variant_b, metric),
        )
        return str(cur.fetchone()[0])


def experiment_list(status="") -> list[dict]:
    q = "SELECT * FROM experiments"
    params: list = []
    if status:
        q += " WHERE status = %s"
        params.append(status)
    q += " ORDER BY id DESC LIMIT 30"
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]


def experiment_update(exp_id: int, **fields) -> bool:
    allowed = {"result_a", "result_b", "status", "winner", "metric"}
    sets = {k: v for k, v in fields.items() if k in allowed and v}
    if not sets:
        return False
    cols = ", ".join(f"{k} = %s" for k in sets)
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            f"UPDATE experiments SET {cols}, updated_at = NOW() WHERE id = %s",
            [*sets.values(), exp_id],
        )
        return cur.rowcount > 0


def decision_log(decision: str, context: str = "", rationale: str = "") -> str:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO decisions (decision, context, rationale) VALUES (%s,%s,%s) RETURNING id",
            (decision, context, rationale),
        )
        return str(cur.fetchone()[0])


def decision_list(limit: int = 40) -> list[dict]:
    with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT %s", (limit,))
        return [dict(r) for r in cur.fetchall()]


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
