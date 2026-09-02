"""Audit trail ('what did you do') + decision journal."""
import database


def what_i_did(hours: int = 24) -> str:
    rows = database.audit_recent(hours)
    if not rows:
        return f"לא ביצעתי שום פעולה שמשנה משהו ב-{hours} השעות האחרונות."
    out = [f"פעולות שביצעתי ב-{hours} השעות האחרונות:"]
    for r in rows:
        ts = r["created_at"].strftime("%d/%m %H:%M")
        out.append(f"  {ts} · {r['action']} — {r['detail'][:160]}")
    return "\n".join(out)


def log_decision(decision: str, context: str = "", rationale: str = "") -> str:
    did = database.decision_log(decision, context, rationale)
    return f"נרשם ביומן החלטות (#{did}): {decision}"


def list_decisions(limit: int = 20) -> str:
    rows = database.decision_list(limit)
    if not rows:
        return "יומן ההחלטות ריק."
    out = []
    for d in rows:
        ts = d["created_at"].strftime("%d/%m")
        line = f"#{d['id']} ({ts}) {d['decision']}"
        if d["rationale"]:
            line += f"\n   למה: {d['rationale']}"
        if d["outcome"]:
            line += f"\n   תוצאה: {d['outcome']}"
        out.append(line)
    return "\n".join(out)


TOOLS = {
    "what_i_did": {
        "schema": {
            "name": "what_i_did",
            "description": "מציג את היומן המלא של הפעולות שהבוט ביצע (מיילים, אירועים, עדכוני מוצר, משימות...). "
            "השתמש כשנועם שואל 'מה עשית היום/השבוע' או 'למה עשית X'.",
            "input_schema": {
                "type": "object",
                "properties": {"hours": {"type": "integer", "description": "כמה שעות אחורה, ברירת מחדל 24"}},
                "required": [],
            },
        },
        "fn": what_i_did,
    },
    "log_decision": {
        "schema": {
            "name": "log_decision",
            "description": (
                "רושם החלטה שנועם קיבל ביומן ההחלטות, עם ההקשר והנימוק. "
                "השתמש כשנועם מחליט משהו מהותי (מחיר, ספק, כיוון עסקי, צבא) — כדי שלא נשאל שוב "
                "ונוכל לזהות דפוסים בעתיד."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string"},
                    "context": {"type": "string"},
                    "rationale": {"type": "string", "description": "למה נועם החליט ככה"},
                },
                "required": ["decision"],
            },
        },
        "fn": log_decision,
    },
    "list_decisions": {
        "schema": {
            "name": "list_decisions",
            "description": "מציג את יומן ההחלטות. השתמש כשנועם שואל 'מה החלטתי לגבי X'.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
                "required": [],
            },
        },
        "fn": list_decisions,
    },
}
