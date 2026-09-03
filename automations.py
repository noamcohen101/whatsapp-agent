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


def growth_move() -> None:
    text = _ask_agent(
        "[אוטומציה — מהלך צמיחה שבועי] הרץ growth_snapshot. "
        "תן לי מהלך צמיחה אחד קונקרטי לבדוק השבוע: מה בדיוק לעשות, למה דווקא זה עכשיו, "
        "ואיך נדע בסוף השבוע אם עבד. משפט על המספרים הרלוונטיים, ואז המהלך. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🚀 *המהלך לשבוע*\n\n{text}")


def trend_jack() -> None:
    text = _ask_agent(
        "[אוטומציה — trend-jacking] חפש (web_search) רגעים חמים בכדורגל ב-24 השעות האחרונות — "
        "גול/משחק יוצא דופן, העברה גדולה, מאמן שפוטר, כותרת ויראלית, השקת מדים. "
        "אם יש משהו שרלוונטי לחולצה ש-Israstore מוכר (woo_list_products): "
        "תגיד לי מיד — איזו חולצה לדחוף, איזה כיתוב לפוסט, ואם שווה מודעה עכשיו. "
        "אם אין שום דבר חם ורלוונטי — החזר בדיוק SKIP. קצר וחד."
    )
    if text.strip().upper().startswith("SKIP"):
        return
    from notify import push

    push("urgent", "רגע חם — הזדמנות", text)


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


def cost_report() -> None:
    from tools.cost import llm_cost

    send_to_phone(BOT_OWNER_PHONE, f"💸 *עלות הבוט השבוע*\n\n{llm_cost(7)}")


def trust_report() -> None:
    text = _ask_agent(
        "[אוטומציה — דוח אמון שבועי] הרץ what_i_did(168). "
        "סכם לי מה עשית לבד השבוע (מיילים, יומן, משימות, follow-ups) — לפי קטגוריות. "
        "כמה פעולות, כמה מהן שגרתיות. היו טעויות או דברים שהייתי צריך לתקן אחריך? "
        "האם יש סוג פעולה שאתה שוב ושוב שואל עליו ואפשר לתת לך אישור עומד? "
        "ולהיפך — משהו שעשית לבד שהיית מעדיף שתשאל? "
        "בסוף: המלצה — לכוונן את רמת האוטונומיה למעלה, למטה, או להשאיר. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🤝 *דוח אמון שבועי*\n\n{text}")


def build_progress() -> None:
    text = _ask_agent(
        "[אוטומציה — התקדמות בנייה] הרץ progress_summary(7) + list_projects. "
        "סכם לי: מה קידמתי השבוע בפרויקטים, מה נשלח/הושלם, על מה נתקעתי (במיוחד אם פעמיים), "
        "ומה הפרויקט שלא זז ואולי צריך תשומת לב או להיסגר. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🛠️ *התקדמות בנייה — השבוע*\n\n{text}")


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


def failed_payment_check() -> None:
    text = _ask_agent(
        "[אוטומציה — תשלומים שנכשלו] הרץ woo_failed_payments (3 ימים). "
        "אלה לקוחות שרצו לקנות והכרטיס נדחה. דווח לי (נועם בלבד) על הרשימה: מי, מה, כמה, מתי. "
        "אל תיצור קשר עם הלקוח — רק דיווח לי. אם אין — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    from notify import push

    push("needs_decision", "תשלומים שנכשלו", text)


def kit_radar() -> None:
    text = _ask_agent(
        "[אוטומציה — ראדאר מדים] חפש (web_search) מדים/חולצות כדורגל חדשים שהושקו "
        "בשבועיים האחרונים — קבוצות גדולות (ריאל, ברצלונה, מנצ'סטר, סיטי, ליברפול, PSG, "
        "באיירן, יובנטוס), נבחרות, וקבוצות ישראליות (מכבי/הפועל). "
        "לכל מדים חדשים שמצאת: בדוק אם Israstore כבר מוכר אותם (woo_list_products). "
        "אם לא — זו הזדמנות: תגיד לי איזה מדים, איזו קבוצה, ולהוסיף מהר. "
        "אם אין מדים חדשים / הכל כבר בחנות — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"👕 *ראדאר מדים חדשים*\n\n{text}")


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
    from op_cycle import operating_cycle

    # Retired jobs — folded into the autonomous operating cycle.
    for old in ("morning_brief", "business_health", "evening_summary",
                "inbox_watch", "follow_up_sweep"):
        try:
            scheduler.remove_job(old)
        except Exception:  # noqa: BLE001
            pass

    # --- The autonomous operating cycle: 3x/day ---
    for slot, hh in (("morning", 9), ("midday", 14), ("evening", 21)):
        scheduler.add_job(
            operating_cycle, CronTrigger(hour=hh, minute=30, timezone=BOT_TIMEZONE),
            id=f"operating_cycle_{slot}", args=[slot],
            replace_existing=True, misfire_grace_time=3600,
        )

    # abandoned cart sweep — once a day
    scheduler.add_job(
        abandoned_carts_check,
        CronTrigger(hour=18, minute=0, timezone=BOT_TIMEZONE),
        id="abandoned_carts", replace_existing=True, misfire_grace_time=3600,
    )
    # failed payment check — twice a day
    scheduler.add_job(
        failed_payment_check,
        CronTrigger(hour="13,20", minute=0, timezone=BOT_TIMEZONE),
        id="failed_payments", replace_existing=True, misfire_grace_time=3600,
    )
    # new kit radar — twice a week
    scheduler.add_job(
        kit_radar,
        CronTrigger(day_of_week="mon,thu", hour=12, minute=0, timezone=BOT_TIMEZONE),
        id="kit_radar", replace_existing=True, misfire_grace_time=7200,
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
    # growth move — Sunday
    scheduler.add_job(
        growth_move,
        CronTrigger(day_of_week="sun", hour=9, minute=0, timezone=BOT_TIMEZONE),
        id="growth_move", replace_existing=True, misfire_grace_time=7200,
    )
    # trust / autonomy report — Saturday evening
    scheduler.add_job(
        trust_report,
        CronTrigger(day_of_week="sat", hour=20, minute=0, timezone=BOT_TIMEZONE),
        id="trust_report", replace_existing=True, misfire_grace_time=7200,
    )
    # build progress — Friday evening
    scheduler.add_job(
        build_progress,
        CronTrigger(day_of_week="fri", hour=19, minute=0, timezone=BOT_TIMEZONE),
        id="build_progress", replace_existing=True, misfire_grace_time=7200,
    )
    # trend-jacking — 3x/day
    scheduler.add_job(
        trend_jack,
        CronTrigger(hour="9,14,20", minute=40, timezone=BOT_TIMEZONE),
        id="trend_jack", replace_existing=True, misfire_grace_time=1800,
    )
    # content calendar — Sunday morning
    scheduler.add_job(
        content_calendar,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=BOT_TIMEZONE),
        id="content_calendar", replace_existing=True, misfire_grace_time=7200,
    )
    # bot cost report — Sunday evening (no LLM call, just DB math)
    scheduler.add_job(
        cost_report,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=BOT_TIMEZONE),
        id="cost_report", replace_existing=True, misfire_grace_time=7200,
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
