"""LLM cost report — estimated from tracked token usage."""
import database

# USD per 1M tokens (input, output). Update if Anthropic pricing changes.
_PRICING = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
}
_USD_TO_ILS = 3.7


def llm_cost(days: int = 7) -> str:
    rows = database.usage_since(days)
    if not rows:
        return f"אין נתוני שימוש ב-{days} הימים האחרונים."
    total_usd = 0.0
    lines = [f"עלות Claude ב-{days} הימים האחרונים (הערכה):", ""]
    for r in rows:
        pin, pout = _PRICING.get(r["model"], (3.0, 15.0))
        cost = (r["in_tok"] or 0) / 1e6 * pin + (r["out_tok"] or 0) / 1e6 * pout
        total_usd += cost
        lines.append(
            f"  {r['model']}: {r['calls']} קריאות · "
            f"{(r['in_tok'] or 0):,} in / {(r['out_tok'] or 0):,} out · ~${cost:.2f}"
        )
    per_day = total_usd / max(days, 1)
    lines.append("")
    lines.append(f"סה\"כ: ~${total_usd:.2f} (~₪{total_usd * _USD_TO_ILS:.0f})")
    lines.append(f"ממוצע יומי: ~${per_day:.2f} · חודשי צפוי: ~${per_day * 30:.2f}")
    return "\n".join(lines)


TOOLS = {
    "llm_cost": {
        "schema": {
            "name": "llm_cost",
            "description": "מראה כמה Claude עולה לנועם (הערכה מטוקנים). days = טווח, ברירת מחדל 7.",
            "input_schema": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
        "fn": llm_cost,
    }
}
