"""Reminders via APScheduler with a SQLite jobstore (survives restarts)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from config import BOT_TIMEZONE, DATABASE_PATH
from tools.whatsapp import send_reply

_TZ = ZoneInfo(BOT_TIMEZONE)

scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{DATABASE_PATH}")},
    timezone=BOT_TIMEZONE,
)


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()


def _fire(chat_id: str, message: str) -> None:
    send_reply(chat_id, f"⏰ תזכורת: {message}")


def create_reminder(chat_id: str, remind_at_iso: str, message: str) -> str:
    """Schedule a reminder. remind_at_iso: ISO 8601 local time, e.g. 2026-09-02T09:00:00."""
    when = datetime.fromisoformat(remind_at_iso)
    if when.tzinfo is None:
        when = when.replace(tzinfo=_TZ)
    if when <= datetime.now(_TZ):
        return "הזמן שביקשת כבר עבר — תן לי זמן עתידי."
    job = scheduler.add_job(
        _fire, "date", run_date=when, args=[chat_id, message], misfire_grace_time=3600
    )
    return f"נקבעה תזכורת ל-{when.strftime('%d/%m %H:%M')} (מזהה {job.id[:8]})."


def list_reminders(chat_id: str) -> str:
    jobs = [j for j in scheduler.get_jobs() if j.args and j.args[0] == chat_id]
    if not jobs:
        return "אין תזכורות פתוחות."
    jobs.sort(key=lambda j: j.next_run_time or datetime.max.replace(tzinfo=_TZ))
    lines = [
        f"- {j.next_run_time.strftime('%d/%m %H:%M')}: {j.args[1]} (מזהה {j.id[:8]})"
        for j in jobs
    ]
    return "תזכורות פתוחות:\n" + "\n".join(lines)


def cancel_reminder(chat_id: str, reminder_id: str) -> str:
    for j in scheduler.get_jobs():
        if j.id.startswith(reminder_id) and j.args and j.args[0] == chat_id:
            j.remove()
            return "התזכורת בוטלה."
    return "לא מצאתי תזכורת עם המזהה הזה."


TOOLS = {
    "create_reminder": {
        "schema": {
            "name": "create_reminder",
            "description": "קובע תזכורת לנועם לזמן עתידי. השתמש כשנועם מבקש 'תזכיר לי...'.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "יתמלא ע\"י המערכת; השאר ריק",
                    },
                    "remind_at_iso": {
                        "type": "string",
                        "description": "זמן התזכורת ב-ISO 8601 מקומי, למשל 2026-09-02T09:00:00",
                    },
                    "message": {
                        "type": "string",
                        "description": "תוכן התזכורת בעברית",
                    },
                },
                "required": ["chat_id", "remind_at_iso", "message"],
            },
        },
        "fn": create_reminder,
    },
    "list_reminders": {
        "schema": {
            "name": "list_reminders",
            "description": "מציג את כל התזכורות הפתוחות של נועם.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "יתמלא ע\"י המערכת; השאר ריק",
                    }
                },
                "required": ["chat_id"],
            },
        },
        "fn": list_reminders,
    },
    "cancel_reminder": {
        "schema": {
            "name": "cancel_reminder",
            "description": "מבטל תזכורת פתוחה לפי המזהה שלה.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "יתמלא ע\"י המערכת; השאר ריק",
                    },
                    "reminder_id": {
                        "type": "string",
                        "description": "מזהה התזכורת (8 התווים שהוצגו)",
                    },
                },
                "required": ["chat_id", "reminder_id"],
            },
        },
        "fn": cancel_reminder,
    },
}
