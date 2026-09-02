"""A/B experiment tracker for ads / product-page copy."""
import database


def start_experiment(name: str, variant_a: str, variant_b: str, metric: str = "") -> str:
    eid = database.experiment_add(name, variant_a, variant_b, metric)
    return f"נפתח ניסוי #{eid}: {name}\nA: {variant_a}\nB: {variant_b}\nמדד: {metric or 'לא צוין'}"


def list_experiments(status: str = "") -> str:
    rows = database.experiment_list(status)
    if not rows:
        return "אין ניסויים."
    out = []
    for e in rows:
        line = f"#{e['id']} [{e['status']}] {e['name']} (מדד: {e['metric'] or '?'})"
        line += f"\n  A: {e['variant_a']} → {e['result_a'] or '—'}"
        line += f"\n  B: {e['variant_b']} → {e['result_b'] or '—'}"
        if e["winner"]:
            line += f"\n  🏆 מנצח: {e['winner']}"
        out.append(line)
    return "\n\n".join(out)


def update_experiment(
    exp_id: int, result_a: str = "", result_b: str = "", status: str = "", winner: str = ""
) -> str:
    ok = database.experiment_update(
        int(exp_id), result_a=result_a, result_b=result_b, status=status, winner=winner
    )
    return "הניסוי עודכן." if ok else "לא מצאתי ניסוי כזה או שלא צוין מה לעדכן."


TOOLS = {
    "start_experiment": {
        "schema": {
            "name": "start_experiment",
            "description": "פותח מעקב אחרי ניסוי A/B (מודעה, טקסט דף מוצר, כותרת). "
            "variant_a/variant_b = שתי הגרסאות. metric = מה מודדים (CTR, המרות, מכירות).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}, "variant_a": {"type": "string"},
                    "variant_b": {"type": "string"}, "metric": {"type": "string"},
                },
                "required": ["name", "variant_a", "variant_b"],
            },
        },
        "fn": start_experiment,
    },
    "list_experiments": {
        "schema": {
            "name": "list_experiments",
            "description": "מציג ניסויים. status אופציונלי: running / done.",
            "input_schema": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": [],
            },
        },
        "fn": list_experiments,
    },
    "update_experiment": {
        "schema": {
            "name": "update_experiment",
            "description": "מעדכן תוצאות ניסוי ומסמן מנצח. status: done כשמסיימים.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "exp_id": {"type": "integer"}, "result_a": {"type": "string"},
                    "result_b": {"type": "string"}, "status": {"type": "string"},
                    "winner": {"type": "string", "description": "A / B"},
                },
                "required": ["exp_id"],
            },
        },
        "fn": update_experiment,
    },
}
