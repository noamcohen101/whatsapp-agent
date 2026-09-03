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
2. **Task Layer — עסקי ואישי כאחד** — list_tasks. מה תקוע? מה אפשר לקדם עכשיו? רדוף follow-ups שהגיע זמנם.
   על משימות אישיות (domain personal/errands): הבטחות שנועם נתן ולא קיים, admin שהוא דוחה, כוונות שחוזרות —
   הזכר לו קצר עם הצעד הבא, והכן מה שאתה יכול (מספר טלפון, טופס, מה להגיד).
3. **יומן** — מה יש היום/מחר. התנגשויות? צריך הכנה למשהו? אירוע אישי שדורש תיאום?
4. **Israstore** — woo_orders_overview + failed_payments + revenue_pace.
   הזמנות בסטטוס processing ששולמו — לכל אחת שנראה שעדיין לא הועברה לספק, הכן הודעה מוכנה לספק
   (woo_prep_supplier_order) והצג לי אותה כדי שאעביר. הזמנות pending ישנות? תשלומים שנכשלו? חריגים?
5. **פרויקטים** — list_projects. מה תקוע יותר מדי זמן? יש פרויקט שלא זז שבוע?
6. **רעיונות ישנים** — אם יש רעיון פתוח שלא נגעו בו הרבה זמן, הזכר אותו קצר ("היה לך רעיון X, עדיין רלוונטי?").
7. **דברים פתוחים בזיכרון / החלטות שממתינות**.

בצע כל מה שמותר לך לבד ותעד. ואז שלח לי דיווח אחד קצר בפורמט:
"עשיתי לבד: [רשימה]. צריך אותך: [רשימה עם מה בדיוק]. שקט על השאר."
אם באמת אין כלום שדורש אותי ולא עשית כלום מיוחד — שלח שורה אחת ש'הכל תחת שליטה'.
פורמט וואטסאפ, *מודגש* עם כוכביות, בלי ## . עד 12 שורות."""

    reply = agent.handle_message(
        f"{BOT_OWNER_PHONE}@c.us", BOT_OWNER_PHONE, instruction,
        context="private", cheap_model=True,
    )
    send_to_phone(BOT_OWNER_PHONE, f"*דיווח תפעול — {when}*\n\n{reply}")
