"""Profit intelligence for Israstore (dropshipping) — net profit, not just revenue."""
import database
from tools.woocommerce import _get


def _f(key: str, default: float = 0.0) -> float:
    v = database.setting_get(key, "")
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def set_profit_inputs(
    cogs_pct: str = "", avg_shipping_cost: str = "", payment_fee_pct: str = "",
    monthly_ad_spend: str = "",
) -> str:
    changed = []
    for key, val in [
        ("cogs_pct", cogs_pct), ("avg_shipping_cost", avg_shipping_cost),
        ("payment_fee_pct", payment_fee_pct), ("monthly_ad_spend", monthly_ad_spend),
    ]:
        if val != "":
            database.setting_set(f"profit_{key}", str(val))
            changed.append(f"{key}={val}")
    return "עודכן: " + ", ".join(changed) if changed else "לא צוין כלום לעדכן."


def profit_analysis(period: str = "month") -> str:
    cogs_pct = _f("profit_cogs_pct")          # e.g. 40 => product costs 40% of sale price
    ship = _f("profit_avg_shipping_cost")     # cost Noam pays supplier for shipping, per order
    fee_pct = _f("profit_payment_fee_pct", 3.5)
    ad_spend = _f("profit_monthly_ad_spend")

    if not cogs_pct:
        return (
            "כדי לחשב רווח אני צריך ממך מספרים. תגיד לי:\n"
            "1) עלות המוצר כאחוז ממחיר המכירה (למשל 40 = החולצה עולה לך 40% ממה שהלקוח משלם)\n"
            "2) עלות משלוח ממוצעת להזמנה (מה שאתה משלם לספק על שילוח)\n"
            "3) עמלת סליקה באחוזים (ברירת מחדל 3.5)\n"
            "4) תקציב פרסום חודשי\n"
            "ואגדיר את זה עם set_profit_inputs."
        )

    data = _get("reports/sales", {"period": period})
    if not data:
        return "אין נתוני מכירות לתקופה."
    d = data[0]
    revenue = float(d.get("total_sales", 0))
    orders = int(d.get("total_orders", 0))
    shipping_collected = float(d.get("total_shipping", 0))

    cogs = revenue * cogs_pct / 100
    ship_cost = ship * orders
    fees = revenue * fee_pct / 100
    ad = ad_spend if period in ("month", "last_month") else ad_spend / 30 * 7
    net = revenue - cogs - ship_cost - fees - ad
    margin = (net / revenue * 100) if revenue else 0

    return (
        f"רווח ({period}):\n"
        f"  הכנסה: {revenue:,.0f}\n"
        f"  - עלות מוצרים ({cogs_pct:.0f}%): {cogs:,.0f}\n"
        f"  - משלוחים ({orders} הזמנות × {ship:.0f}): {ship_cost:,.0f}\n"
        f"  - עמלות סליקה ({fee_pct:.1f}%): {fees:,.0f}\n"
        f"  - פרסום: {ad:,.0f}\n"
        f"  = רווח נטו: {net:,.0f} ({margin:.0f}% מרווח)\n"
        f"  (משלוח שנגבה מלקוחות: {shipping_collected:,.0f})"
    )


TOOLS = {
    "set_profit_inputs": {
        "schema": {
            "name": "set_profit_inputs",
            "description": "מגדיר את המספרים לחישוב רווח: cogs_pct (אחוז עלות מוצר), avg_shipping_cost, "
            "payment_fee_pct, monthly_ad_spend. השתמש כשנועם נותן את המספרים.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cogs_pct": {"type": "string"},
                    "avg_shipping_cost": {"type": "string"},
                    "payment_fee_pct": {"type": "string"},
                    "monthly_ad_spend": {"type": "string"},
                },
                "required": [],
            },
        },
        "fn": set_profit_inputs,
    },
    "profit_analysis": {
        "schema": {
            "name": "profit_analysis",
            "description": "מחשב רווח נטו (לא רק הכנסה) לתקופה — אחרי עלות מוצר, משלוח, עמלות ופרסום. "
            "period: week/month/last_month/year.",
            "input_schema": {
                "type": "object",
                "properties": {"period": {"type": "string"}},
                "required": [],
            },
        },
        "fn": profit_analysis,
    },
}
