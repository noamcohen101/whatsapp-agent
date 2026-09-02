"""Gmail tool (read-only): search / read / summarize the user's inbox."""
import base64
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN


def _service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _plain_body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="replace")
    for part in payload.get("parts", []):
        body = _plain_body(part)
        if body:
            return body
    # fall back to html stripped-ish
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        html = base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="replace")
        import re

        return re.sub(r"<[^>]+>", " ", html)
    return ""


def search_emails(query: str = "", max_results: int = 10) -> str:
    svc = _service()
    res = (
        svc.users()
        .messages()
        .list(userId="me", q=query or "in:inbox", maxResults=min(max_results, 20))
        .execute()
    )
    ids = [m["id"] for m in res.get("messages", [])]
    if not ids:
        return "לא נמצאו מיילים."
    lines = []
    for mid in ids:
        msg = (
            svc.users()
            .messages()
            .get(userId="me", id=mid, format="metadata",
                 metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        p = msg.get("payload", {})
        frm = _header(p, "From")
        subj = _header(p, "Subject") or "(ללא נושא)"
        snippet = msg.get("snippet", "")[:120]
        unread = "UNREAD" in msg.get("labelIds", [])
        mark = "🔵 " if unread else ""
        lines.append(f"{mark}[{mid}] מאת {frm}\n  {subj}\n  {snippet}")
    return "\n\n".join(lines)


def get_email(message_id: str) -> str:
    svc = _service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    p = msg.get("payload", {})
    frm = _header(p, "From")
    subj = _header(p, "Subject") or "(ללא נושא)"
    date = _header(p, "Date")
    body = _plain_body(p).strip()[:6000]
    return f"מאת: {frm}\nנושא: {subj}\nתאריך: {date}\n\n{body}"


TOOLS = {
    "search_emails": {
        "schema": {
            "name": "search_emails",
            "description": (
                "מחפש מיילים בתיבה של נועם. query בתחביר Gmail "
                "(למשל 'from:paypal', 'is:unread', 'subject:חשבונית', 'newer_than:7d'). "
                "השאר ריק כדי לקבל את המיילים האחרונים בתיבה."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "שאילתת חיפוש בתחביר Gmail"},
                    "max_results": {"type": "integer", "description": "כמה תוצאות, ברירת מחדל 10"},
                },
                "required": [],
            },
        },
        "fn": search_emails,
    },
    "get_email": {
        "schema": {
            "name": "get_email",
            "description": "קורא את התוכן המלא של מייל לפי ה-id שלו (מתקבל מ-search_emails).",
            "input_schema": {
                "type": "object",
                "properties": {"message_id": {"type": "string", "description": "מזהה המייל"}},
                "required": ["message_id"],
            },
        },
        "fn": get_email,
    },
}
