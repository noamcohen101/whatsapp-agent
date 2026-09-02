"""Scheduled proactive automations — recurring jobs that push updates to Noam.

Each job asks the agent (with full tool access) to produce something, then sends
it to Noam's private chat. Job functions must stay module-level so APScheduler's
Postgres jobstore can serialize them across restarts.
"""
from apscheduler.triggers.cron import CronTrigger

from config import BOT_OWNER_PHONE, BOT_TIMEZONE
from tools.whatsapp import send_to_phone

_OWNER_CHAT = f"{BOT_OWNER_PHONE}@c.us"


def _ask_agent(instruction: str) -> str:
    # imported lazily to avoid a circular import at module load
    import agent

    return agent.handle_message(_OWNER_CHAT, BOT_OWNER_PHONE, instruction, context="private")


_FMT = (
    "פורמט: וואטסאפ בלבד — *מודגש* עם כוכביות, בלי כותרות markdown (##). "
    "קצר ותפעולי, עד 8-10 שורות. רק מה שבאמת חשוב. "
    "אם אין כלום מיוחד — 2-3 שורות ש'היום שקט'."
)


def morning_brief() -> None:
    text = _ask_agent(
        "[אוטומציה — בריף בוקר] עבור לבד על: היומן היום, מיילים חשובים שנכנסו "
        "(לא ספאם/שיווק), הזמנות pending ומלאי נמוך ב-Israstore, ודברים פתוחים בזיכרון. "
        "תן: מה חייב לקרות היום, מה כדאי לדחות, על מה צריך החלטה ממני. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"☀️ *בריף בוקר*\n\n{text}")


def evening_summary() -> None:
    text = _ask_agent(
        "[אוטומציה — סיכום ערב] מה נסגר היום, מה נשאר פתוח, מה מחכה לאחרים, "
        "מה יש מחר ביומן, ומה כדאי שאדע לפני סוף היום. " + _FMT
    )
    send_to_phone(BOT_OWNER_PHONE, f"🌙 *סיכום יום*\n\n{text}")


def business_health_check() -> None:
    text = _ask_agent(
        "[אוטומציה — בריאות עסק] בדוק שהכל תקין ב-Israstore: "
        "1) fetch_page על https://israstore.shop — האתר עולה ותקין? "
        "2) woo_orders_overview — יש קפיצה חריגה ב-failed/cancelled? "
        "3) woo_list_products low_stock_only=true — מלאי קריטי? "
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
        "רק למשלוחים שסומנו 🔔 (השתנה סטטוס): הכן טיוטת עדכון קצר ואדיב ללקוח בוואטסאפ "
        "(איפה החבילה / מתי צפויה). הצג לי טיוטה + טלפון הלקוח, אני אאשר. "
        "אם שום דבר לא השתנה — החזר בדיוק SKIP. " + _FMT
    )
    if text.strip().upper().startswith("SKIP"):
        return
    send_to_phone(BOT_OWNER_PHONE, f"📦 *עדכוני משלוחים*\n\n{text}")


def abandoned_carts_check() -> None:
    text = _ask_agent(
        "[אוטומציה — עגלות נטושות] בדוק עגלות נטושות (woo_abandoned_checkouts). "
        "אם אין — אל תשלח כלום, תחזיר בדיוק את המילה SKIP. "
        "אם יש — לכל עגלה הכן טיוטת הודעת שחזור קצרה ואדיבה בוואטסאפ ללקוח "
        "(מזכירה את הפריט, אולי שאלה אם צריך עזרה, בלי הנחה אלא אם אני מאשר). "
        "הצג לי את הרשימה + הטיוטות. אני אאשר מה לשלוח. " + _FMT
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
    # abandoned cart sweep 3x/day
    scheduler.add_job(
        abandoned_carts_check,
        CronTrigger(hour="12,17,21", minute=30, timezone=BOT_TIMEZONE),
        id="abandoned_carts", replace_existing=True, misfire_grace_time=3600,
    )
    # competitor price watch — once a day
    scheduler.add_job(
        competitor_price_watch,
        CronTrigger(hour=11, minute=0, timezone=BOT_TIMEZONE),
        id="competitor_prices", replace_existing=True, misfire_grace_time=7200,
    )
    # shipment status sweep — twice a day
    scheduler.add_job(
        shipment_updates,
        CronTrigger(hour="9,19", minute=15, timezone=BOT_TIMEZONE),
        id="shipment_updates", replace_existing=True, misfire_grace_time=3600,
    )
