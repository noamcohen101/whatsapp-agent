"""Personal money tools: expense log, savings goal tracking. Separate from Israstore/business tools."""
from collections import defaultdict
from datetime import datetime

import database


def log_expense(amount: float, category: str = "כללי", note: str = "") -> str:
    database.expense_add(amount, category, note)
    return f"נרשם: {amount:,.0f} ₪ · {category}" + (f" · {note}" if note else "")


def personal_expense_summary(days: int = 30) -> str:
    rows = database.expense_list(days)
    if not rows:
        return f"אין הוצאות רשומות ב-{days} הימים האחרונים."
    by_cat: dict[str, float] = defaultdict(float)
    total = 0.0
    for r in rows:
        by_cat[r["category"]] += float(r["amount"])
        total += float(r["amount"])
    lines = [f"הוצאות אישיות ב-{days} הימים האחרונים — סה\"כ {total:,.0f} ₪:"]
    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = amt / total * 100 if total else 0
        lines.append(f"  • {cat}: {amt:,.0f} ₪ ({pct:.0f}%)")
    return "\n".join(lines)


def set_savings_goal(name: str, target_amount: float, target_date: str = "") -> str:
    database.savings_goal_set(name, target_amount, target_date)
    until = f" עד {target_date}" if target_date else ""
    return f"נקבע יעד חיסכון: {name} — {target_amount:,.0f} ₪{until}."


def log_savings(amount: float, note: str = "") -> str:
    goal = database.savings_goal_active()
    if not goal:
        return "אין יעד חיסכון פעיל כרגע. תגיד לי 'קבע יעד חיסכון' קודם."
    database.savings_log_add(goal["id"], amount, note)
    saved = database.savings_log_total(goal["id"])
    target = float(goal["target_amount"])
    pct = saved / target * 100 if target else 0
    return f"נרשם! נחסך {saved:,.0f} מתוך {target:,.0f} ₪ ({pct:.0f}%) ליעד '{goal['name']}'."


def savings_progress() -> str:
    goal = database.savings_goal_active()
    if not goal:
        return "אין יעד חיסכון פעיל. תגיד לי 'קבע יעד חיסכון X ₪' כדי להתחיל לעקוב."
    saved = database.savings_log_total(goal["id"])
    target = float(goal["target_amount"])
    remaining = max(target - saved, 0)
    pct = saved / target * 100 if target else 0
    lines = [
        f"יעד: {goal['name']} — {target:,.0f} ₪",
        f"נחסך עד כה: {saved:,.0f} ₪ ({pct:.0f}%)",
        f"נשאר: {remaining:,.0f} ₪",
    ]
    if goal.get("target_date"):
        try:
            td = datetime.fromisoformat(goal["target_date"]).date()
            days_left = (td - datetime.now().date()).days
            if days_left > 0:
                lines.append(f"עד {goal['target_date']} — {days_left} ימים, כלומר ~{remaining/days_left:,.0f} ₪ ליום.")
            else:
                lines.append("תאריך היעד כבר עבר.")
        except ValueError:
            pass
    return "\n".join(lines)


TOOLS = {
    "log_expense": {
        "schema": {
            "name": "log_expense",
            "description": (
                "רושם הוצאה אישית (לא עסקית/Israstore). קרא לזה בכל פעם שנועם מזכיר "
                "שהוא שילם/הוציא כסף על משהו אישי, גם בלי שביקש מפורשות לרשום."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "סכום בש\"ח"},
                    "category": {"type": "string", "description": "קטגוריה, למשל אוכל/תחבורה/בילויים/קניות"},
                    "note": {"type": "string", "description": "פרטים קצרים, אופציונלי"},
                },
                "required": ["amount"],
            },
        },
        "fn": log_expense,
    },
    "personal_expense_summary": {
        "schema": {
            "name": "personal_expense_summary",
            "description": "מציג פירוט הוצאות אישיות לפי קטגוריה לתקופה. השתמש כשנועם שואל 'כמה הוצאתי'.",
            "input_schema": {
                "type": "object",
                "properties": {"days": {"type": "integer", "description": "כמה ימים אחורה, ברירת מחדל 30"}},
                "required": [],
            },
        },
        "fn": personal_expense_summary,
    },
    "set_savings_goal": {
        "schema": {
            "name": "set_savings_goal",
            "description": "קובע יעד חיסכון אישי חדש (מחליף את הקודם אם היה). השתמש כשנועם אומר שהוא רוצה לחסוך למשהו.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "למה חוסכים, למשל 'טיול לכריתים'"},
                    "target_amount": {"type": "number"},
                    "target_date": {"type": "string", "description": "תאריך יעד ISO YYYY-MM-DD, אופציונלי"},
                },
                "required": ["name", "target_amount"],
            },
        },
        "fn": set_savings_goal,
    },
    "log_savings": {
        "schema": {
            "name": "log_savings",
            "description": "רושם שנועם הפריש כסף ליעד החיסכון הפעיל. השתמש כשהוא אומר 'שמתי בצד X'.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "note": {"type": "string"},
                },
                "required": ["amount"],
            },
        },
        "fn": log_savings,
    },
    "savings_progress": {
        "schema": {
            "name": "savings_progress",
            "description": "מציג התקדמות מול יעד החיסכון הפעיל. השתמש כשנועם שואל 'כמה חסכתי' / 'כמה נשאר'.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": savings_progress,
    },
}
