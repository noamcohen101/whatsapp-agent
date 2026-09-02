"""Scheduled proactive automations — recurring jobs that push updates to Noam.

Each job asks the agent (with full tool access) to produce something, then sends
it to Noam's private chat. Job functions must stay module-level so APScheduler's
Postgres jobstore can serialize them across restarts.
"""
from apscheduler.triggers.cron import CronTrigger

from config import BOT_OWNER_PHONE, BOT_TIMEZONE
from tools.whatsapp import send_to_phone

_OWNER_CHAT = f"{BOT_OWNER_PHONE}@c.us"


def _ask_agent(instruction: str) -> str:
    # imported lazily to avoid a circular import at module load
    import agent

    return agent.handle_message(_OWNER_CHAT, BOT_OWNER_PHONE, instruction, context="private")


_FMT = (
    "פורמט: וואטסאפ בלבד — *מודגש* עם כוכביות, בלי כותרות markdown (##). "
    "קצר ותפעולי, עד 8-10 שורות. רק מה שבאמת חשוב. "
    "אם אין כלום מיוחד — 2-3 שורות ש'היום שקט'."
)


def morning_brief() -> None:
    text = _ask_agent(
        "[אוטומציה — בריף בוקר] עבור לבד על: היומן היום, מיילים חשובים שנכנסו "
        "(לא ספאם/שיווק), הזמנות pending ומלאי נמוך ב-Israstore, ודברים פתוחים בזיכרון. "
        "תן: מה חייב לקרות היום, מה כדאי לדחות, על מה צריך החלטה ממני. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"☀️ *בריף בוקר*\n\n{text}")


def evening_summary() -> None:
    text = _ask_agent(
        "[אוטומציה — סיכום ערב] מה נסגר היום, מה נשאר פתוח, מה מחכה לאחרים, "
        "מה יש מחר ביומן, ומה כדאי שאדע לפני סוף היום. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🌙 *סיכום יום*\n\n{text}")


def register(scheduler) -> None:
    """Add the recurring automation jobs (idempotent — replace_existing)."""
    scheduler.add_job(
        morning_brief, CronTrigger(hour=10, minute=0, timezone=BOT_TIMEZONE),
        id="morning_brief", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.add_job(
        evening_summary, CronTrigger(hour=22, minute=0, timezone=BOT_TIMEZONE),
        id="evening_summary", replace_existing=True, misfire_grace_time=3600,
    )
