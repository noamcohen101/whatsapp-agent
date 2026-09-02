"""The autonomous operating cycle — one brain that runs the show a few times a day.

Replaces the scattered morning-brief / inbox-watch / follow-up / health-check jobs
with a single coherent pass: process, act on what's allowed, surface only what needs Noam.
"""
from config import BOT_OWNER_PHONE
from tools.whatsapp import send_to_phone

_LABEL = {"morning": "☀️ בוקר", "midday": "🕑 צהריים", "evening": "🌙 ערב"}


def operating_cycle(slot: str = "midday") -> None:
    import agent
    import database

    if database.setting_get("safety_state", "normal") == "paused":
        return

    when = _LABEL.get(slot, "סבב")
    instruction = f"""[מנוע תפעול אוטונומי — סבב {when}]
עבור על הכל, טפל במה שמותר לך לבד (רמת אוטונומיה בינונית), והעלה לי רק מה שדורש אותי.

1. **מיילים** — search_emails 'is:unread newer_than:1d'. סווג כל אחד: שגרתי / דורש החלטה / דחוף / ספאם.
   על שגרתי — טפל לבד (טיוטה + שליחה מותרת לתשובות שגרתיות). על השאר — פתח משימה או סמן לי.
2. **Task Layer** — list_tasks. מה תקוע? מה אפשר לקדם עכשיו? רדוף follow-ups שהגיע זמנם. עדכן סטטוסים.
3. **יומן** — מה יש היום/מחר. התנגשויות? צריך הכנה למשהו?
4. **Israstore** — woo_orders_overview + failed_payments + abandoned_checkouts + revenue_pace.
   הזמנות pending ישנות? תשלומים שנכשלו? חריגים?
5. **דברים פתוחים בזיכרון / החלטות שממתינות**.

בצע כל מה שמותר לך לבד ותעד. ואז שלח לי דיווח אחד קצר בפורמט:
"עשיתי לבד: [רשימה]. צריך אותך: [רשימה עם מה בדיוק]. שקט על השאר."
אם באמת אין כלום שדורש אותי ולא עשית כלום מיוחד — שלח שורה אחת ש'הכל תחת שליטה'.
פורמט וואטסאפ, *מודגש* עם כוכביות, בלי ## . עד 12 שורות."""

    reply = agent.handle_message(
        f"{BOT_OWNER_PHONE}@c.us", BOT_OWNER_PHONE, instruction, context="private"
    )
    send_to_phone(BOT_OWNER_PHONE, f"*דיווח תפעול — {when}*\n\n{reply}")
