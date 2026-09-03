"""Idea vault + build progress log."""
import database


def save_idea(idea: str, category: str = "general", notes: str = "") -> str:
    iid = database.idea_add(idea, category, notes)
    return f"נשמר רעיון #{iid}: {idea}"


def list_ideas(status: str = "open") -> str:
    rows = database.idea_list(status)
    if not rows:
        return "מאגר הרעיונות ריק."
    by_cat: dict[str, list] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(
            f"#{r['id']} {r['idea']}" + (f" — {r['notes']}" if r["notes"] else "")
        )
    out = []
    for cat, items in by_cat.items():
        out.append(f"*{cat}*")
        out += [f"  • {i}" for i in items]
    return "\n".join(out)


def update_idea(idea_id: int, status: str = "", notes: str = "", category: str = "") -> str:
    ok = database.idea_update(int(idea_id), status=status, notes=notes, category=category)
    return "עודכן." if ok else "לא מצאתי רעיון כזה."


def progress_summary(days: int = 7) -> str:
    logs = database.project_log_since(days)
    if not logs:
        return f"אין לוג פעילות ב-{days} הימים האחרונים."
    by_proj: dict[str, list] = {}
    for l in logs:
        by_proj.setdefault(l["name"], []).append(
            f"{l['created_at'].strftime('%d/%m')} — {l['note']}"
        )
    out = [f"התקדמות ב-{days} הימים האחרונים:", ""]
    for name, notes in by_proj.items():
        out.append(f"*{name}* ({len(notes)} סשנים)")
        out += [f"  {n}" for n in notes]
        out.append("")
    return "\n".join(out)


TOOLS = {
    "save_idea": {
        "schema": {
            "name": "save_idea",
            "description": (
                "שומר רעיון של נועם למאגר. השתמש בכל פעם שנועם זורק רעיון — לפרויקט, לפיצ'ר, "
                "לעסק, למשהו לבנות. category: product / business / feature / content / general."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "idea": {"type": "string"},
                    "category": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["idea"],
            },
        },
        "fn": save_idea,
    },
    "list_ideas": {
        "schema": {
            "name": "list_ideas",
            "description": "מציג את מאגר הרעיונות. status: open / promoted / dropped / all.",
            "input_schema": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": [],
            },
        },
        "fn": list_ideas,
    },
    "update_idea": {
        "schema": {
            "name": "update_idea",
            "description": "מעדכן רעיון — status (promoted כשהופך לפרויקט / dropped), הערות, קטגוריה.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "idea_id": {"type": "integer"},
                    "status": {"type": "string"},
                    "notes": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["idea_id"],
            },
        },
        "fn": update_idea,
    },
    "progress_summary": {
        "schema": {
            "name": "progress_summary",
            "description": "מסכם מה נועם קידם/בנה בפרויקטים ב-X הימים האחרונים (מיומני הסשנים).",
            "input_schema": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
        "fn": progress_summary,
    },
}
