"""Revenue-vs-target pace + customer segmentation for Israstore (dropshipping)."""
import calendar
from collections import defaultdict
from datetime import datetime, timezone

import database
from tools.woocommerce import _get


def set_revenue_target(monthly_target: str) -> str:
    database.setting_set("revenue_target_monthly", str(monthly_target))
    return f"נקבע יעד הכנסה חודשי: {monthly_target}."


def revenue_pace() -> str:
    target = database.setting_get("revenue_target_monthly", "")
    now = datetime.now(timezone.utc)
    data = _get("reports/sales", {"period": "month"})
    total = float(data[0].get("total_sales", 0)) if data else 0.0
    orders = int(data[0].get("total_orders", 0)) if data else 0
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    day = now.day
    projection = total / day * days_in_month if day else 0

    lines = [
        f"החודש עד עכשיו (יום {day}/{days_in_month}): {total:,.0f} · {orders} הזמנות",
        f"קצב שנתי-לחודש (תחזית סוף חודש): ~{projection:,.0f}",
    ]
    if target:
        t = float(target)
        expected_by_now = t / days_in_month * day
        gap = total - expected_by_now
        pct = (total / t * 100) if t else 0
        status = "מעל הקצב 🔥" if gap >= 0 else "מתחת לקצב ⚠️"
        lines.append(
            f"יעד חודשי: {t:,.0f} · השגת {pct:.0f}% · {status} "
            f"(אמור להיות ~{expected_by_now:,.0f} עד היום, פער {gap:+,.0f})"
        )
    else:
        lines.append("אין יעד חודשי מוגדר — תגיד לי 'קבע יעד X' כדי לעקוב מול יעד.")
    return "\n".join(lines)


def customer_segments(scan_orders: int = 150) -> str:
    """Segment customers from recent orders: VIP / repeat / one-time / dormant."""
    orders = _get(
        "orders",
        {"per_page": min(scan_orders, 100), "orderby": "date", "order": "desc",
         "status": "completed,processing"},
    )
    by_cust: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "total": 0.0, "last": None, "name": ""}
    )
    for o in orders:
        b = o.get("billing", {})
        key = (b.get("email") or b.get("phone") or "").strip().lower()
        if not key:
            continue
        d = by_cust[key]
        d["count"] += 1
        d["total"] += float(o.get("total", 0) or 0)
        dt = o["date_created"][:10]
        if not d["last"] or dt > d["last"]:
            d["last"] = dt
        d["name"] = f"{b.get('first_name','')} {b.get('last_name','')}".strip() or key

    today = datetime.now(timezone.utc).date()
    vip, repeat, dormant = [], [], []
    for key, d in by_cust.items():
        last = datetime.strptime(d["last"], "%Y-%m-%d").date() if d["last"] else None
        days_ago = (today - last).days if last else 999
        tag = f"{d['name']} · {d['count']} הזמנות · {d['total']:,.0f} · אחרונה לפני {days_ago} ימים"
        if d["count"] >= 3 or d["total"] >= 800:
            vip.append(tag)
        elif d["count"] >= 2:
            repeat.append(tag)
        if days_ago >= 60 and d["count"] >= 1:
            dormant.append(tag)

    out = [f"פילוח לקוחות (מתוך {len(by_cust)} לקוחות ב-{len(orders)} הזמנות אחרונות):", ""]
    out.append(f"**VIP ({len(vip)})** — 3+ הזמנות או 800+ ש\"ח:")
    out += [f"  • {x}" for x in vip[:12]] or ["  (אין)"]
    out.append(f"\n**חוזרים ({len(repeat)})** — 2 הזמנות:")
    out += [f"  • {x}" for x in repeat[:10]] or ["  (אין)"]
    out.append(f"\n**רדומים ({len(dormant)})** — לא קנו 60+ יום:")
    out += [f"  • {x}" for x in dormant[:12]] or ["  (אין)"]
    out.append(
        "\nהצעות: VIP — גישה מוקדמת לדרופים / קוד אישי. "
        "חוזרים — דחיפה קלה להזמנה שלישית. רדומים — קמפיין 'חזרה' (רק אם נועם מאשר; הבוט לא יוזם)."
    )
    return "\n".join(out)


def set_purchase_gate(amount: str) -> str:
    database.setting_set("purchase_gate_amount", str(amount))
    return f"נקבע סף בקרת קנייה: {amount}. מעכשיו לפני כל קנייה מעל הסכום הזה אשאל אותך 3 שאלות."


TOOLS = {
    "set_purchase_gate": {
        "schema": {
            "name": "set_purchase_gate",
            "description": "קובע סכום שמעליו הבוט עוצר לפני קנייה ושואל 3 שאלות. השתמש כשנועם אומר 'תעצור אותי לפני קניות מעל X'.",
            "input_schema": {
                "type": "object",
                "properties": {"amount": {"type": "string"}},
                "required": ["amount"],
            },
        },
        "fn": set_purchase_gate,
    },
    "set_revenue_target": {
        "schema": {
            "name": "set_revenue_target",
            "description": "קובע יעד הכנסה חודשי למעקב. השתמש כשנועם אומר 'קבע יעד X'.",
            "input_schema": {
                "type": "object",
                "properties": {"monthly_target": {"type": "string", "description": "סכום בש\"ח/דולר"}},
                "required": ["monthly_target"],
            },
        },
        "fn": set_revenue_target,
    },
    "revenue_pace": {
        "schema": {
            "name": "revenue_pace",
            "description": "מראה הכנסות החודש מול היעד ותחזית סוף חודש. השתמש לכל שאלה על 'איך אנחנו עומדים החודש'.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": revenue_pace,
    },
    "customer_segments": {
        "schema": {
            "name": "customer_segments",
            "description": "מפלח את הלקוחות: VIP / חוזרים / רדומים, עם הצעת פעולה לכל קבוצה.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": customer_segments,
    },
}
