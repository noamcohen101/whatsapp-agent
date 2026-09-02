"""Shipment tracking for Israstore orders (supplier ships from China via 4PX/E-post/Cheetah)."""
import os

import httpx

import database
from tools.web_search import fetch_page, web_search
from tools.woocommerce import _get

TRACKINGMORE_KEY = os.getenv("TRACKINGMORE_API_KEY", "")


def _order_contact(order_id: str) -> tuple[str, str]:
    try:
        o = _get(f"orders/{order_id}")
        b = o.get("billing", {})
        name = f"{b.get('first_name','')} {b.get('last_name','')}".strip()
        return name, (b.get("phone") or "")
    except Exception:  # noqa: BLE001
        return "", ""


def link_shipment(order_id: str, tracking_number: str, carrier: str = "") -> str:
    tracking_number = tracking_number.strip().replace(" ", "")
    name, phone = _order_contact(order_id)
    sid = database.add_shipment(order_id, tracking_number, carrier, name, phone)
    return (
        f"קושר: הזמנה #{order_id} ← מעקב {tracking_number} ({carrier or 'לא ידוע'})\n"
        f"לקוח: {name or '?'} · {phone or 'אין טלפון'}\n"
        f"אעקוב ואעדכן אותך כשהסטטוס משתנה (מזהה משלוח {sid})."
    )


def _track_one(tracking_number: str, carrier: str) -> str:
    if TRACKINGMORE_KEY:
        try:
            r = httpx.post(
                "https://api.trackingmore.com/v4/trackings/realtime",
                headers={"Tracking-Api-Key": TRACKINGMORE_KEY, "Content-Type": "application/json"},
                json={"tracking_number": tracking_number, "courier_code": carrier or None},
                timeout=25,
            )
            data = r.json().get("data", {})
            sub = data.get("delivery_status") or data.get("status") or "unknown"
            last = (data.get("origin_info", {}).get("trackinfo") or [{}])[0].get("tracking_detail", "")
            return f"{sub} — {last}"
        except Exception as e:  # noqa: BLE001
            return f"[שגיאת TrackingMore] {e}"
    # best-effort: search the web for the tracking number
    res = web_search(f"{tracking_number} tracking status", max_results=3)
    for line in res.splitlines():
        line = line.strip()
        if line.startswith("http"):
            return fetch_page(line, max_chars=1500)
    return res[:800]


def check_shipments() -> str:
    ships = database.active_shipments()
    if not ships:
        return "אין משלוחים פעילים במעקב."
    out = []
    for s in ships:
        status = _track_one(s["tracking_number"], s["carrier"])
        changed = status.strip()[:60] != (s["last_status"] or "").strip()[:60]
        delivered = any(w in status.lower() for w in ("delivered", "נמסר", "signed"))
        database.update_shipment_status(s["id"], status.strip()[:200], deactivate=delivered)
        mark = "🔔 " if changed else ""
        out.append(
            f"{mark}#{s['order_id']} · {s['customer_name']} · {s['tracking_number']}\n"
            f"  {status[:300]}"
        )
    return "\n\n".join(out)


TOOLS = {
    "link_shipment": {
        "schema": {
            "name": "link_shipment",
            "description": (
                "מקשר מספר מעקב להזמנה ומתחיל לעקוב. השתמש כשנועם נותן מספר מעקב מהספק "
                "(לרוב מתמונה) ואומר לאיזו הזמנה. carrier: 4px / e-post / cheetah / china-post וכו'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "tracking_number": {"type": "string"},
                    "carrier": {"type": "string"},
                },
                "required": ["order_id", "tracking_number"],
            },
        },
        "fn": link_shipment,
    },
    "check_shipments": {
        "schema": {
            "name": "check_shipments",
            "description": "בודק את כל המשלוחים הפעילים ומחזיר סטטוס עדכני. 🔔 = היה שינוי.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": check_shipments,
    },
}
