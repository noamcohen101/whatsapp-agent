"""Task Layer — the bot's internal source of truth for open items across all domains."""
import database

_DOMAINS = "army / business / money / errands / personal / general"


def add_task(
    title: str,
    domain: str = "general",
    priority: str = "normal",
    due: str = "",
    next_action: str = "",
    waiting_on: str = "",
    source: str = "",
) -> str:
    tid = database.task_add(
        title, domain, priority, due, next_action, waiting_on, source
    )
    return f"נוספה משימה #{tid}: {title} ({domain}, {priority})"


def list_tasks(status: str = "open", domain: str = "") -> str:
    rows = database.task_list(status, domain)
    if not rows:
        return "אין משימות פתוחות." if status == "open" else "אין משימות."
    out = []
    for t in rows:
        bits = [f"#{t['id']} [{t['priority']}] {t['title']}"]
        meta = []
        if t["domain"] != "general":
            meta.append(t["domain"])
        if t["due"]:
            meta.append(f"עד {t['due']}")
        if t["waiting_on"]:
            meta.append(f"ממתין ל-{t['waiting_on']}")
        if t["next_action"]:
            meta.append(f"→ {t['next_action']}")
        if t["status"] != "open":
            meta.append(t["status"])
        if meta:
            bits.append("  " + " · ".join(meta))
        out.append("\n".join(bits))
    return "\n".join(out)


def update_task(
    task_id: int,
    status: str = "",
    priority: str = "",
    due: str = "",
    next_action: str = "",
    waiting_on: str = "",
    title: str = "",
    notes: str = "",
) -> str:
    ok = database.task_update(
        int(task_id),
        status=status, priority=priority, due=due, next_action=next_action,
        waiting_on=waiting_on, title=title, notes=notes,
    )
    return "המשימה עודכנה." if ok else "לא מצאתי משימה כזו או שלא צוין מה לשנות."


TOOLS = {
    "add_task": {
        "schema": {
            "name": "add_task",
            "description": (
                "מוסיף משימה ל-Task Layer הפנימי. השתמש כשנועם אומר לך לזכור לעשות משהו, "
                "או כשאתה מזהה next-action ממייל/שיחה/הזמנה. " f"domain: {_DOMAINS}. "
                "priority: urgent / high / normal / low."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "domain": {"type": "string"},
                    "priority": {"type": "string"},
                    "due": {"type": "string", "description": "תאריך יעד, טקסט חופשי או ISO"},
                    "next_action": {"type": "string", "description": "הצעד הבא הקונקרטי"},
                    "waiting_on": {"type": "string", "description": "אם ממתין למישהו/משהו"},
                    "source": {"type": "string", "description": "מאיפה זה בא (מייל/שיחה/הזמנה)"},
                },
                "required": ["title"],
            },
        },
        "fn": add_task,
    },
    "list_tasks": {
        "schema": {
            "name": "list_tasks",
            "description": "מציג משימות. status: open (ברירת מחדל) / done / waiting / all. domain אופציונלי.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "domain": {"type": "string"},
                },
                "required": [],
            },
        },
        "fn": list_tasks,
    },
    "update_task": {
        "schema": {
            "name": "update_task",
            "description": (
                "מעדכן משימה לפי id — לסמן done/waiting, לשנות עדיפות, דדליין, next_action, "
                "waiting_on או כותרת. השתמש כשמשהו זז או נסגר."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {"type": "string", "description": "open / done / waiting / cancelled"},
                    "priority": {"type": "string"},
                    "due": {"type": "string"},
                    "next_action": {"type": "string"},
                    "waiting_on": {"type": "string"},
                    "title": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["task_id"],
            },
        },
        "fn": update_task,
    },
}
