"""Proactive push to Noam with interruption levels + quiet hours."""
from datetime import datetime
from zoneinfo import ZoneInfo

from config import BOT_OWNER_PHONE, BOT_TIMEZONE
from tools.whatsapp import send_to_phone

_TZ = ZoneInfo(BOT_TIMEZONE)

# 01:00–08:00: only 'critical' gets through; everything else waits for the
# morning brief (the bot already collects it via the audit/task tables).
_QUIET_START, _QUIET_END = 1, 8

_ICON = {"fyi": "ℹ️", "needs_decision": "🤔", "urgent": "⏰", "critical": "🚨"}


def push(level: str, title: str, body: str) -> bool:
    """level: fyi | needs_decision | urgent | critical. Returns True if sent now."""
    hour = datetime.now(_TZ).hour
    quiet = _QUIET_START <= hour < _QUIET_END
    if quiet and level != "critical":
        return False
    send_to_phone(BOT_OWNER_PHONE, f"{_ICON.get(level, '•')} *{title}*\n\n{body}")
    return True
