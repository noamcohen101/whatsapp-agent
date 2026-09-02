"""Growth analysis input bundle — gathers the raw material; the agent synthesizes the move."""
from tools.woocommerce import _get


def growth_snapshot() -> str:
    out = ["חומר גלם לניתוח צמיחה:\n"]

    try:
        this_m = _get("reports/sales", {"period": "month"})[0]
        last_m = _get("reports/sales", {"period": "last_month"})[0]
        out.append(
            f"מכירות: החודש {float(this_m['total_sales']):,.0f} ({this_m['total_orders']} הזמנות) · "
            f"חודש שעבר {float(last_m['total_sales']):,.0f} ({last_m['total_orders']} הזמנות)"
        )
    except Exception as e:  # noqa: BLE001
        out.append(f"מכירות: שגיאה — {e}")

    try:
        top = _get("products", {"orderby": "popularity", "order": "desc", "per_page": 8, "status": "publish"})
        out.append("מוצרים מובילים: " + ", ".join(f"{p['name']} ({p.get('price','')}₪)" for p in top))
    except Exception as e:  # noqa: BLE001
        out.append(f"מוצרים: שגיאה — {e}")

    try:
        totals = _get("reports/orders/totals")
        by = {t["slug"]: t["total"] for t in totals}
        out.append(
            f"סטטוס הזמנות: הושלמו {by.get('completed',0)} · בטיפול {by.get('processing',0)} · "
            f"בוטלו {by.get('cancelled',0)} · נכשלו {by.get('failed',0)} · pending {by.get('pending',0)}"
        )
    except Exception as e:  # noqa: BLE001
        out.append(f"סטטוסים: שגיאה — {e}")

    out.append(
        "\nמשימה: על סמך זה + מה שאתה יודע על Israstore, המתחרים והשוק — "
        "תן מהלך צמיחה אחד קונקרטי לבדוק השבוע (מה בדיוק לעשות, למה דווקא זה, ואיך נדע אם עבד). "
        "לא רשימה — מהלך אחד, הכי גבוה-מנוף."
    )
    return "\n".join(out)


TOOLS = {
    "growth_snapshot": {
        "schema": {
            "name": "growth_snapshot",
            "description": "אוסף תמונת מצב של העסק (מכירות, מוצרים, סטטוסים) לצורך המלצת מהלך צמיחה. "
            "השתמש כשנועם שואל 'מה המהלך הבא' / 'איך מגדילים'.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": growth_snapshot,
    }
}
