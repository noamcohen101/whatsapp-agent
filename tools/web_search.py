"""Web search + page fetch. Keyless (DuckDuckGo). Swap to Brave/Tavily later if needed."""
import re

import httpx
from ddgs import DDGS


def web_search(query: str, max_results: int = 6) -> str:
    try:
        results = list(DDGS().text(query, max_results=min(max_results, 10)))
    except Exception as e:  # noqa: BLE001
        return f"[שגיאת חיפוש] {e}"
    if not results:
        return "לא נמצאו תוצאות."
    lines = []
    for r in results:
        title = r.get("title", "")
        href = r.get("href", "")
        body = (r.get("body", "") or "")[:200]
        lines.append(f"• {title}\n  {href}\n  {body}")
    return "\n\n".join(lines)


def fetch_page(url: str, max_chars: int = 4000) -> str:
    try:
        resp = httpx.get(
            url,
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WhatsAppAgent/1.0)"},
        )
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        return f"[שגיאת טעינת עמוד] {e}"
    html = resp.text
    html = re.sub(r"(?is)<(script|style|noscript|head).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


TOOLS = {
    "web_search": {
        "schema": {
            "name": "web_search",
            "description": (
                "חיפוש באינטרנט למידע עדכני — מחירים, חדשות, תוצאות ספורט, מוצרים, "
                "מתחרים, טרנדים. מחזיר כותרות, קישורים ותקצירים."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "מה לחפש"},
                    "max_results": {"type": "integer", "description": "כמות תוצאות, ברירת מחדל 6"},
                },
                "required": ["query"],
            },
        },
        "fn": web_search,
    },
    "fetch_page": {
        "schema": {
            "name": "fetch_page",
            "description": "מוריד וקורא את הטקסט של עמוד אינטרנט לפי URL (למשל תוצאה מ-web_search).",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "כתובת העמוד"}},
                "required": ["url"],
            },
        },
        "fn": fetch_page,
    },
}
