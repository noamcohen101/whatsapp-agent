"""Project chief-of-staff — track every thing Noam is building: state, next step, blockers."""
import database


def update_project(
    name: str, goal: str = "", next_step: str = "", blocker: str = "",
    status: str = "", priority: str = "",
) -> str:
    database.project_upsert(
        name, goal=goal, next_step=next_step, blocker=blocker,
        status=status, priority=priority,
    )
    return f"עודכן פרויקט '{name}'."


def log_session(project: str, note: str) -> str:
    """End-of-session note: what got done, where Noam is stuck. Kept as running context."""
    database.project_add_log(project, note)
    return f"נרשם ליומן של '{project}'. אחזיר לך את זה בפעם הבאה שתחזור לפרויקט."


def list_projects(status: str = "active") -> str:
    rows = database.project_list(status)
    if not rows:
        return "אין פרויקטים פעילים. תגיד לי על מה אתה עובד ואתחיל לעקוב."
    out = []
    for p in rows:
        line = f"*{p['name']}* [{p['priority']}]"
        if p["goal"]:
            line += f"\n  מטרה: {p['goal']}"
        if p["next_step"]:
            line += f"\n  → הצעד הבא: {p['next_step']}"
        if p["blocker"]:
            line += f"\n  ⛔ תקוע: {p['blocker']}"
        out.append(line)
    return "\n\n".join(out)


def project_context(name: str) -> str:
    p = database.project_get(name)
    if not p:
        return f"אין לי פרויקט בשם '{name}'. תגיד לי עליו ואתחיל לעקוב."
    out = [f"*{p['name']}* — {p['status']}"]
    if p["goal"]:
        out.append(f"מטרה: {p['goal']}")
    if p["next_step"]:
        out.append(f"הצעד הבא: {p['next_step']}")
    if p["blocker"]:
        out.append(f"תקוע ב: {p['blocker']}")
    if p["recent_log"]:
        out.append("\nמהסשנים האחרונים:")
        for l in p["recent_log"]:
            out.append(f"  {l['created_at'].strftime('%d/%m')} — {l['note']}")
    return "\n".join(out)


TOOLS = {
    "update_project": {
        "schema": {
            "name": "update_project",
            "description": (
                "יוצר/מעדכן פרויקט שנועם עובד עליו. השתמש כשנועם מזכיר פרויקט, מטרה, צעד הבא או משהו שתקוע. "
                "status: active / paused / done. priority: high / normal / low."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "goal": {"type": "string"},
                    "next_step": {"type": "string"},
                    "blocker": {"type": "string"},
                    "status": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        "fn": update_project,
    },
    "log_session": {
        "schema": {
            "name": "log_session",
            "description": (
                "רושם הערת סוף-סשן על פרויקט — מה נעשה, איפה נועם נתקע. "
                "השתמש כשנועם מספר על מה עבד. אחזיר לו את זה כשיחזור לפרויקט."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["project", "note"],
            },
        },
        "fn": log_session,
    },
    "list_projects": {
        "schema": {
            "name": "list_projects",
            "description": "מציג את כל הפרויקטים הפעילים עם הצעד הבא והתקיעות. status אופציונלי.",
            "input_schema": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": [],
            },
        },
        "fn": list_projects,
    },
    "project_context": {
        "schema": {
            "name": "project_context",
            "description": "מחזיר את כל ההקשר של פרויקט מסוים — מטרה, צעד הבא, תקיעות, והסשנים האחרונים. "
            "השתמש כשנועם שואל 'מה עשיתי ב-X' / 'איפה עצרנו ב-X' / חוזר לעבוד על פרויקט.",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        "fn": project_context,
    },
}
