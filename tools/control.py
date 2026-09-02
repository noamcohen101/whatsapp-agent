"""Standing approvals + global safety state (kill switch) for the autonomous bot."""
from datetime import datetime, timedelta, timezone

import database

# safety_state: normal | read_only | paused
_STATES = {"normal", "read_only", "paused"}


def set_safety_state(state: str) -> str:
    state = state.strip().lower()
    if state not in _STATES:
        return "מצב לא מוכר. אפשר: normal / read_only / paused."
    database.setting_set("safety_state", state)
    msg = {
        "normal": "חזרתי לפעילות מלאה ✅",
        "read_only": "מצב קריאה בלבד — אני קורא ומדווח, לא מבצע כלום 👀",
        "paused": "עצרתי הכל ⏸️ — לא פועל ולא מדווח עד שתגיד 'חזור'.",
    }[state]
    return msg


def get_safety_state() -> str:
    s = database.setting_get("safety_state", "normal")
    return f"מצב נוכחי: {s}"


def add_standing_approval(rule: str, hours: int = 0, days: int = 0) -> str:
    exp = None
    if hours or days:
        exp = datetime.now(timezone.utc) + timedelta(hours=hours, days=days)
    aid = database.approval_add(rule, exp)
    until = f" (עד {exp.strftime('%d/%m %H:%M')})" if exp else " (עד ביטול)"
    return f"נרשם אישור עומד #{aid}: {rule}{until}"


def list_standing_approvals() -> str:
    rows = database.approval_list()
    if not rows:
        return "אין אישורים עומדים. כל פעולה רגישה דורשת אישור נקודתי."
    out = ["אישורים עומדים פעילים:"]
    for r in rows:
        until = f" (עד {r['expires_at'].strftime('%d/%m %H:%M')})" if r["expires_at"] else ""
        out.append(f"  #{r['id']} {r['rule']}{until}")
    return "\n".join(out)


def revoke_standing_approval(approval_id: int) -> str:
    return "בוטל." if database.approval_revoke(int(approval_id)) else "לא מצאתי אישור כזה."


TOOLS = {
    "set_safety_state": {
        "schema": {
            "name": "set_safety_state",
            "description": (
                "משנה את מצב הבטיחות הגלובלי. normal = פעילות מלאה. "
                "read_only = הבוט רק קורא ומדווח. paused = הבוט לא עושה כלום. "
                "השתמש כשנועם אומר 'עצור הכל' / 'מצב קריאה' / 'חזור לפעילות'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"state": {"type": "string"}},
                "required": ["state"],
            },
        },
        "fn": set_safety_state,
    },
    "add_standing_approval": {
        "schema": {
            "name": "add_standing_approval",
            "description": (
                "רושם אישור מראש לסוג פעולה, כדי שהבוט לא ישאל בכל פעם. "
                "למשל 'לאשר הזמנות מהספק עד $50', 'לשלוח תשובות ללקוחות על סטטוס הזמנה היום'. "
                "hours/days = תוקף (0 = עד ביטול). השתמש כשנועם נותן אישור גורף."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "hours": {"type": "integer"},
                    "days": {"type": "integer"},
                },
                "required": ["rule"],
            },
        },
        "fn": add_standing_approval,
    },
    "list_standing_approvals": {
        "schema": {
            "name": "list_standing_approvals",
            "description": "מציג את האישורים העומדים הפעילים.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": list_standing_approvals,
    },
    "revoke_standing_approval": {
        "schema": {
            "name": "revoke_standing_approval",
            "description": "מבטל אישור עומד לפי id.",
            "input_schema": {
                "type": "object",
                "properties": {"approval_id": {"type": "integer"}},
                "required": ["approval_id"],
            },
        },
        "fn": revoke_standing_approval,
    },
}
