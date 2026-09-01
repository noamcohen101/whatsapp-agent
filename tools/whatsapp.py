"""Green API outbound helpers. Framework-only — not exposed as LLM tools."""
import httpx

from config import GREEN_API_INSTANCE, GREEN_API_TOKEN, GREEN_API_URL

_BASE = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE}"


def _chat_id_from_phone(phone_e164: str) -> str:
    digits = phone_e164.lstrip("+").strip()
    return digits if digits.endswith("@c.us") else f"{digits}@c.us"


def send_reply(chat_id: str, text: str) -> dict:
    """Send a text message to a chat_id (already in NNN@c.us / NNN@g.us form)."""
    resp = httpx.post(
        f"{_BASE}/sendMessage/{GREEN_API_TOKEN}",
        json={"chatId": chat_id, "message": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_to_phone(phone_e164: str, text: str) -> dict:
    return send_reply(_chat_id_from_phone(phone_e164), text)


def download_file(url: str) -> bytes:
    resp = httpx.get(url, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    return resp.content
