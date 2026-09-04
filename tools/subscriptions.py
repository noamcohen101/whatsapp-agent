"""Scan Gmail for recurring charges / subscriptions."""
from tools.gmail import search_emails

_QUERIES = [
    'subject:(receipt OR invoice OR "payment" OR subscription OR renew) newer_than:120d',
    'subject:(קבלה OR חשבונית OR חיוב OR מנוי OR חידוש) newer_than:120d',
    'from:(paypal.com OR stripe.com OR paddle.com) newer_than:120d',
    'subject:(netflix OR spotify OR icloud OR "google one" OR "חדר כושר" OR gym) newer_than:120d',
]


def scan_subscriptions() -> str:
    blocks = []
    for q in _QUERIES:
        res = search_emails(q, max_results=12)
        if res and "לא נמצאו" not in res:
            blocks.append(f"### חיפוש: {q}\n{res}")
    if not blocks:
        return "לא מצאתי מיילים של חיובים/מנויים ב-120 הימים האחרונים."
    return (
        "\n\n".join(blocks)
        + "\n\nנתח: אילו חיובים חוזרים כל חודש? יש כפילויות (משלמים פעמיים על אותו שירות)? "
        "מה מתחדש בקרוב? מה אפשר לבטל?"
    )


TOOLS = {
    "scan_subscriptions": {
        "schema": {
            "name": "scan_subscriptions",
            "description": (
                "סורק את ה-Gmail אחרי חיובים חוזרים ומנויים — גם אישיים (Netflix, חדר כושר, אפליקציות) "
                "וגם עסקיים (קבלות, חשבוניות, PayPal/Stripe). "
                "השתמש כשנועם שואל על מנויים / חיובים / 'על מה אני משלם' / 'לצוד לי מנויים שסורקים כסף'."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": scan_subscriptions,
    }
}
