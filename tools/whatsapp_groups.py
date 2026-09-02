"""Read WhatsApp group history on demand (private chat only)."""
import httpx

from config import GREEN_API_INSTANCE, GREEN_API_TOKEN, GREEN_API_URL, SPEC

_GROUPS = {
    g["name"]: g["chat_id"]
    for g in SPEC.get("tools_config", {}).get("whatsapp_groups", {}).get("allowed_groups", [])
}
_BASE = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE}"


def _resolve(name: str) -> str | None:
    if name in _GROUPS:
        return _GROUPS[name]
    low = name.strip().lower()
    for gname, cid in _GROUPS.items():
        if low in gname.lower() or gname.lower() in low:
            return cid
    # single group -> just use it
    if len(_GROUPS) == 1:
        return next(iter(_GROUPS.values()))
    return None


def group_history(group_name: str = "", last_n: int = 40) -> str:
    chat_id = _resolve(group_name)
    if not chat_id:
        return "לא מצאתי קבוצה כזאת. הקבוצות שאני מכיר: " + ", ".join(_GROUPS) if _GROUPS else "אין קבוצות מוגדרות."
    r = httpx.post(
        f"{_BASE}/getChatHistory/{GREEN_API_TOKEN}",
        json={"chatId": chat_id, "count": min(last_n, 100)},
        timeout=30,
    )
    r.raise_for_status()
    msgs = r.json()
    if not msgs:
        return "אין הודעות בהיסטוריה של הקבוצה."
    lines = []
    for m in msgs:
        who = m.get("senderName") or m.get("chatName") or "?"
        txt = m.get("textMessage") or m.get("caption") or f"[{m.get('typeMessage','מדיה')}]"
        lines.append(f"{who}: {txt}")
    return "\n".join(lines[-last_n:])


TOOLS = {
    "read_group_history": {
        "schema": {
            "name": "read_group_history",
            "description": (
                "קורא את ההודעות האחרונות בקבוצת וואטסאפ של Israstore. "
                "השתמש כשנועם מבקש לסכם או לבדוק מה נאמר בקבוצה."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "group_name": {"type": "string", "description": "שם הקבוצה, אופציונלי אם יש רק אחת"},
                    "last_n": {"type": "integer", "description": "כמה הודעות אחרונות, ברירת מחדל 40"},
                },
                "required": [],
            },
        },
        "fn": group_history,
    }
}
