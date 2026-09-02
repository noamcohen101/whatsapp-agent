"""Scheduled proactive automations — recurring jobs that push updates to Noam.

Each job asks the agent (with full tool access) to produce something, then sends
it to Noam's private chat. Job functions must stay module-level so APScheduler's
Postgres jobstore can serialize them across restarts.
"""
from apscheduler.triggers.cron import CronTrigger

from config import BOT_OWNER_PHONE, BOT_TIMEZONE
from tools.whatsapp import send_to_phone

_OWNER_CHAT = f"{BOT_OWNER_PHONE}@c.us"


def _ask_agent(instruction: str, cheap: bool = False) -> str:
    # imported lazily to avoid a circular import at module load
    import agent

    return agent.handle_message(
        _OWNER_CHAT, BOT_OWNER_PHONE, instruction, context="private", cheap_model=cheap
    )


_FMT = (
    "פורמט: וואטסאפ בלבד — *מודגש* עם כוכביות, בלי כותרות markdown (##). "
    "קצר ותפעולי, עד 8-10 שורות. רק מה שבאמת חשוב. "
    "אם אין כלום מיוחד — 2-3 שורות ש'היום שקט'."
)


def morning_brief() -> None:
    text = _ask_agent(
        "[אוטומציה — בריף בוקר] עבור לבד על: היומן היום, מיילים חשובים שנכנסו "
        "(לא ספאם/שיווק), הזמנות pending ב-Israstore, קצב הכנסות מול היעד (revenue_pace), ודברים פתוחים בזיכרון. "
        "תן: מה חייב לקרות היום, מה כדאי לדחות, על מה צריך החלטה ממני. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"☀️ *בריף בוקר*\n\n{text}")


def evening_summary() -> None:
    text = _ask_agent(
        "[אוטומציה — סיכום ערב] מה נסגר היום, מה נשאר פתוח, מה מחכה לאחרים, "
        "מה יש מחר ביומן, ומה כדאי שאדע לפני סוף היום. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🌙 *סיכום יום*\n\n{text}")


def content_calendar() -> None:
    text = _ask_agent(
        "[אוטומציה — לוח תוכן שבועי] חפש (web_search) את משחקי הכדורגל הגדולים השבוע "
        "(ליגות מובילות, צ'מפיונס, נבחרות, דרבי). בדוק אילו חולצות רלוונטיות נמכרות ב-Israstore. "
        "הצע לוח תוכן לשבוע: אילו פוסטים/סטוריז, מתי (סביב המשחקים), איזו חולצה לדחוף בכל אחד, "
        "וזווית קצרה לכל פוסט. אם אין משחקים בולטים — הצע 2-3 רעיונות כלליים. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"📅 *לוח תוכן לשבוע*\n\n{text}")


def meeting_prep() -> None:
    text = _ask_agent(
        "[אוטומציה — הכנה לפגישות מחר] בדוק את היומן של מחר (list_calendar_events). "
        "לכל פגישה חשובה עם אדם/חברה (לא Deep Work / זמן אישי): הכן תיק קצר — "
        "מי האדם/החברה (web_search אם צריך), רקע מהמיילים (search_emails), "
        "מה מטרת הפגישה, ומה חשוב לסגור. "
        "אם אין פגישות חשובות מחר — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"📋 *הכנה לפגישות מחר*\n\n{text}")


def weekly_review() -> None:
    text = _ask_agent(
        "[אוטומציה — סקירה שבועית] סכם לי את השבוע: מה נסגר, קצב הכנסות מול יעד (revenue_pace), "
        "פילוח לקוחות קצר (customer_segments — VIP חדשים? רדומים חדשים?), "
        "מה נשאר פתוח וחשוב (list_tasks), מה נדחה שוב ושוב, ומה 3 הדברים הכי חשובים לשבוע הבא. "
        "אם אתה רואה דפוס (למשל 'שוב דחית החלטת מחיר') — תגיד לי אותו ישר. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🗓️ *סקירה שבועית*\n\n{text}")


def reputation_scan() -> None:
    text = _ask_agent(
        "[אוטומציה — מוניטין] חפש (web_search) אזכורים חדשים של 'Israstore' / 'israstore.shop' — "
        "ביקורות, פוסטים, תלונות, המלצות. דווח רק אם מצאת משהו חדש שדורש תשומת לב "
        "(במיוחד שלילי). אם אין כלום חדש — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"📣 *מוניטין*\n\n{text}")


def inbox_watch() -> None:
    """A few times a day: surface a genuinely important new email that needs action."""
    text = _ask_agent(
        "[אוטומציה — מעקב אינבוקס] חפש מיילים לא-נקראים מהיום "
        "(search_emails 'is:unread newer_than:1d'). "
        "האם נכנס משהו שבאמת דורש תשומת לב — לקוח שמחכה, ספק, PayPal/אשראי, "
        "משהו רשמי, דדליין? אם כן — משפט-שניים על מה זה ומה הצעד. "
        "אם רק שיווק/ספאם/כלום דחוף — החזר בדיוק SKIP. קצר מאוד."
    )
    if text.strip().upper().startswith("SKIP"):
        return
    from notify import push

    push("urgent", "מייל שדורש טיפול", text)


def follow_up_sweep() -> None:
    import database

    tasks = database.task_list("open") + database.task_list("waiting")
    if not tasks:
        return
    text = _ask_agent(
        "[אוטומציה — רדיפה] עבור על המשימות הפתוחות (list_tasks). "
        "אילו תקועות — עברו הדדליין, או ממתינות למישהו יותר מיומיים, או לא זזו הרבה זמן? "
        "לכל אחת: מה הצעד כדי לזוז. אם הכל בשליטה — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    from notify import push

    push("needs_decision", "משימות תקועות", text)


def subscription_review() -> None:
    text = _ask_agent(
        "[אוטומציה — מנויים] הרץ scan_subscriptions. דווח לי: אילו חיובים חוזרים כל חודש, "
        "יש כפילויות, מה מתחדש בקרוב, ומה כדאי לבטל. אם לא מצאת כלום חדש מאז הפעם הקודמת — SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"💳 *מנויים וחיובים חוזרים*\n\n{text}")


def business_health_check() -> None:
    text = _ask_agent(
        "[אוטומציה — בריאות עסק] בדוק שהכל תקין ב-Israstore: "
        "1) fetch_page על https://israstore.shop — האתר עולה ותקין? "
        "2) woo_orders_overview — יש קפיצה חריגה ב-failed/cancelled? "
        "3) revenue_pace — האם אנחנו בקצב מול היעד החודשי? "
        "4) הזמנות pending ישנות (מעל יומיים)? "
        "5) מיילים מ-PayPal/אשראי/ספק ב-24 שעות אחרונות שדורשים טיפול? "
        "החזר: '✅ הכל תקין' אם אין בעיות, אחרת רשימת הבעיות לפי דחיפות. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🩺 *בדיקת בריאות עסק*\n\n{text}")


def competitor_price_watch() -> None:
    from tools.competitors import israstore_top_sellers

    try:
        tops = israstore_top_sellers(4)
    except Exception:  # noqa: BLE001
        tops = []
    if not tops:
        return
    text = _ask_agent(
        "[אוטומציה — ריגול מחירים] השווה מחירים מול המתחרים "
        f"(compare_competitor_prices) עבור המוצרים הכי נמכרים: {', '.join(tops)}. "
        "דווח רק על מוצרים שבהם יש פער מחיר משמעותי (Israstore יקר/זול ב-15%+ ממתחרה), "
        "עם המלצת מהלך. אם אין פערים משמעותיים — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"🔍 *ריגול מחירים*\n\n{text}")


def shipment_updates() -> None:
    import database

    if not database.active_shipments():
        return
    text = _ask_agent(
        "[אוטומציה — מעקב משלוחים] הרץ check_shipments. "
        "דווח לי (נועם בלבד) על משלוחים שסומנו 🔔 (השתנה סטטוס): איפה החבילה, "
        "ואם משהו תקוע/בעייתי. אל תכין ואל תשלח שום הודעה ללקוח — הבוט לא יוזם קשר. "
        "אם שום דבר לא השתנה — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"📦 *עדכוני משלוחים*\n\n{text}")


def abandoned_carts_check() -> None:
    text = _ask_agent(
        "[אוטומציה — עגלות נטושות] בדוק עגלות נטושות (woo_abandoned_checkouts) — הזמנות שלא שולמו = הכנסה שאבדה. "
        "אם אין — החזר בדיוק SKIP. "
        "אם יש — דווח לי (נועם בלבד) על הרשימה: מי, מה בעגלה, כמה זמן. "
        "אל תכין ואל תשלח שום הודעה ללקוח — הבוט לא יוזם קשר. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"🛒 *עגלות נטושות*\n\n{text}")


def register(scheduler) -> None:
    """Add the recurring automation jobs (idempotent — replace_existing)."""
    scheduler.add_job(
        morning_brief, CronTrigger(hour=10, minute=0, timezone=BOT_TIMEZONE),
        id="morning_brief", replace_existing=True, misfire_grace_time=3600,
    )
    # business health check — every morning before the brief
    scheduler.add_job(
        business_health_check, CronTrigger(hour=9, minute=30, timezone=BOT_TIMEZONE),
        id="business_health", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.add_job(
        evening_summary, CronTrigger(hour=22, minute=0, timezone=BOT_TIMEZONE),
        id="evening_summary", replace_existing=True, misfire_grace_time=3600,
    )
    # abandoned cart sweep — once a day
    scheduler.add_job(
        abandoned_carts_check,
        CronTrigger(hour=18, minute=0, timezone=BOT_TIMEZONE),
        id="abandoned_carts", replace_existing=True, misfire_grace_time=3600,
    )
    # competitor price watch — once a week (Sunday)
    scheduler.add_job(
        competitor_price_watch,
        CronTrigger(day_of_week="sun", hour=11, minute=0, timezone=BOT_TIMEZONE),
        id="competitor_prices", replace_existing=True, misfire_grace_time=7200,
    )
    # shipment status sweep — twice a day
    scheduler.add_job(
        shipment_updates,
        CronTrigger(hour="9,19", minute=15, timezone=BOT_TIMEZONE),
        id="shipment_updates", replace_existing=True, misfire_grace_time=3600,
    )
    # weekly review — Friday morning
    scheduler.add_job(
        weekly_review,
        CronTrigger(day_of_week="fri", hour=9, minute=0, timezone=BOT_TIMEZONE),
        id="weekly_review", replace_existing=True, misfire_grace_time=7200,
    )
    # content calendar — Sunday morning
    scheduler.add_job(
        content_calendar,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=BOT_TIMEZONE),
        id="content_calendar", replace_existing=True, misfire_grace_time=7200,
    )
    # inbox watch — 3x/day
    scheduler.add_job(
        inbox_watch,
        CronTrigger(hour="11,15,19", minute=5, timezone=BOT_TIMEZONE),
        id="inbox_watch", replace_existing=True, misfire_grace_time=1800,
    )
    # follow-up sweep — twice a day
    scheduler.add_job(
        follow_up_sweep,
        CronTrigger(hour="10,18", minute=45, timezone=BOT_TIMEZONE),
        id="follow_up_sweep", replace_existing=True, misfire_grace_time=3600,
    )
    # reputation scan — twice a week (Sun + Wed)
    scheduler.add_job(
        reputation_scan,
        CronTrigger(day_of_week="sun,wed", hour=13, minute=0, timezone=BOT_TIMEZONE),
        id="reputation_scan", replace_existing=True, misfire_grace_time=7200,
    )
    # meeting prep — evening before
    scheduler.add_job(
        meeting_prep,
        CronTrigger(hour=20, minute=30, timezone=BOT_TIMEZONE),
        id="meeting_prep", replace_existing=True, misfire_grace_time=3600,
    )
    # subscription review — 1st of the month
    scheduler.add_job(
        subscription_review,
        CronTrigger(day=1, hour=12, minute=0, timezone=BOT_TIMEZONE),
        id="subscription_review", replace_existing=True, misfire_grace_time=86400,
    )
