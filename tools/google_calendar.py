"""Google Calendar tool: list / create / move / delete events on the primary calendar."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import (
    BOT_TIMEZONE,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN,
)

_TZ = ZoneInfo(BOT_TIMEZONE)


def _service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _fmt(ev: dict) -> str:
    s = ev.get("start", {})
    when = s.get("dateTime") or s.get("date", "")
    try:
        when = datetime.fromisoformat(when).astimezone(_TZ).strftime("%d/%m %H:%M")
    except ValueError:
        pass
    title = ev.get("summary", "(ללא כותרת)")
    return f"- {when} — {title} (id: {ev['id']})"


def list_events(time_min_iso: str = "", time_max_iso: str = "") -> str:
    now = datetime.now(_TZ)
    tmin = datetime.fromisoformat(time_min_iso) if time_min_iso else now
    tmax = datetime.fromisoformat(time_max_iso) if time_max_iso else now + timedelta(days=1)
    if tmin.tzinfo is None:
        tmin = tmin.replace(tzinfo=_TZ)
    if tmax.tzinfo is None:
        tmax = tmax.replace(tzinfo=_TZ)
    res = (
        _service()
        .events()
        .list(
            calendarId="primary",
            timeMin=tmin.isoformat(),
            timeMax=tmax.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=25,
        )
        .execute()
    )
    items = res.get("items", [])
    if not items:
        return "אין אירועים בטווח הזה."
    return "\n".join(_fmt(e) for e in items)


def _is_date_only(s: str) -> bool:
    return len(s.strip()) == 10 and s.strip()[4] == "-" and "T" not in s


def create_event(
    summary: str, start_iso: str, end_iso: str = "", attendees: str = ""
) -> str:
    # All-day / multi-day event when only a date is given (e.g. a trip).
    if _is_date_only(start_iso):
        sd = datetime.fromisoformat(start_iso).date()
        if end_iso and _is_date_only(end_iso):
            ed = datetime.fromisoformat(end_iso).date()
        else:
            ed = sd
        # Google's all-day end date is exclusive — add one day so the last day is included.
        body = {
            "summary": summary,
            "start": {"date": sd.isoformat()},
            "end": {"date": (ed + timedelta(days=1)).isoformat()},
        }
        ev = _service().events().insert(calendarId="primary", body=body).execute()
        return f"נקבע (יום שלם): {summary} {sd.strftime('%d/%m')}–{ed.strftime('%d/%m')} (id: {ev['id']})"

    start = datetime.fromisoformat(start_iso)
    if start.tzinfo is None:
        start = start.replace(tzinfo=_TZ)
    end = datetime.fromisoformat(end_iso) if end_iso and not _is_date_only(end_iso) else start + timedelta(hours=1)
    if end.tzinfo is None:
        end = end.replace(tzinfo=_TZ)
    body = {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": BOT_TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": BOT_TIMEZONE},
    }
    if attendees:
        body["attendees"] = [{"email": a.strip()} for a in attendees.split(",") if a.strip()]
    ev = _service().events().insert(calendarId="primary", body=body).execute()
    return f"נקבע: {summary} ב-{start.strftime('%d/%m %H:%M')} (id: {ev['id']})"


def update_event(
    event_id: str, summary: str = "", start_iso: str = "", end_iso: str = ""
) -> str:
    svc = _service()
    ev = svc.events().get(calendarId="primary", eventId=event_id).execute()
    if summary:
        ev["summary"] = summary
    if start_iso:
        s = datetime.fromisoformat(start_iso)
        if s.tzinfo is None:
            s = s.replace(tzinfo=_TZ)
        ev["start"] = {"dateTime": s.isoformat(), "timeZone": BOT_TIMEZONE}
        if not end_iso:
            e = s + timedelta(hours=1)
            ev["end"] = {"dateTime": e.isoformat(), "timeZone": BOT_TIMEZONE}
    if end_iso:
        e = datetime.fromisoformat(end_iso)
        if e.tzinfo is None:
            e = e.replace(tzinfo=_TZ)
        ev["end"] = {"dateTime": e.isoformat(), "timeZone": BOT_TIMEZONE}
    out = svc.events().update(calendarId="primary", eventId=event_id, body=ev).execute()
    return f"עודכן: {out.get('summary')} (id: {out['id']})"


def delete_event(event_id: str) -> str:
    _service().events().delete(calendarId="primary", eventId=event_id).execute()
    return "האירוע נמחק."


TOOLS = {
    "list_calendar_events": {
        "schema": {
            "name": "list_calendar_events",
            "description": "מציג אירועים ביומן של נועם בין שני זמנים. השאר ריק כדי לקבל את 24 השעות הקרובות.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "time_min_iso": {"type": "string", "description": "תחילת הטווח ISO 8601, אופציונלי"},
                    "time_max_iso": {"type": "string", "description": "סוף הטווח ISO 8601, אופציונלי"},
                },
                "required": [],
            },
        },
        "fn": list_events,
    },
    "create_calendar_event": {
        "schema": {
            "name": "create_calendar_event",
            "description": "קובע אירוע חדש ביומן. להזזת אירוע קיים אל תשתמש בזה — השתמש ב-update_calendar_event. אל תיצור פעמיים.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "כותרת האירוע"},
                    "start_iso": {"type": "string", "description": "התחלה. עם שעה: ISO מלא 2026-09-22T11:00:00. ליום שלם / טיול: רק תאריך 2026-09-22"},
                    "end_iso": {"type": "string", "description": "סיום. ליום שלם רב-ימי: תאריך היום האחרון בפועל (כולל). אופציונלי"},
                    "attendees": {"type": "string", "description": "מיילים מופרדים בפסיק, אופציונלי"},
                },
                "required": ["summary", "start_iso"],
            },
        },
        "fn": create_event,
    },
    "update_calendar_event": {
        "schema": {
            "name": "update_calendar_event",
            "description": "מזיז או מעדכן אירוע קיים לפי id. דורש אישור מנועם לפני קריאה.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "מזהה האירוע"},
                    "summary": {"type": "string", "description": "כותרת חדשה, אופציונלי"},
                    "start_iso": {"type": "string", "description": "התחלה חדשה ISO 8601, אופציונלי"},
                    "end_iso": {"type": "string", "description": "סיום חדש ISO 8601, אופציונלי"},
                },
                "required": ["event_id"],
            },
        },
        "fn": update_event,
    },
    "delete_calendar_event": {
        "schema": {
            "name": "delete_calendar_event",
            "description": "מוחק אירוע לפי id. דורש אישור מפורש מנועם לפני קריאה.",
            "input_schema": {
                "type": "object",
                "properties": {"event_id": {"type": "string", "description": "מזהה האירוע"}},
                "required": ["event_id"],
            },
        },
        "fn": delete_event,
    },
}
