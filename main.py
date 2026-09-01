"""FastAPI app: Green API webhook -> agent -> reply."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

import agent
import database
from config import APP_VERSION, BOT_OWNER_PHONE, SPEC
from prompt import build_system_prompt
from tools import TOOL_REGISTRY
from tools.whatsapp import download_file, send_reply
from transcription import transcribe

# --- whitelist (non-bypassable, enforced here not in the prompt) ---
_WHITELIST = {BOT_OWNER_PHONE} | {
    c["phone_e164"].lstrip("+")
    for c in SPEC.get("audience", {}).get("authorized_contacts", [])
}
_ANSWER_GROUPS = SPEC.get("audience", {}).get("answer_groups", False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    if "reminders" in SPEC.get("tools", []):
        from tools.reminders import start_scheduler

        start_scheduler()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(debug: str | None = None):
    if debug == "prompt":
        return {"prompt": build_system_prompt(SPEC, TOOL_REGISTRY)}
    return {"status": "ok", "version": APP_VERSION, "tools": list(TOOL_REGISTRY)}


def _extract_text(message_data: dict) -> str | None:
    t = message_data.get("typeMessage")
    if t == "textMessage":
        return message_data.get("textMessageData", {}).get("textMessage")
    if t in ("extendedTextMessage", "quotedMessage"):
        return message_data.get("extendedTextMessageData", {}).get("text")
    return None


def _extract_audio_url(message_data: dict) -> tuple[str, str] | None:
    t = message_data.get("typeMessage")
    if t not in ("audioMessage", "voiceMessage"):
        return None
    fm = message_data.get("fileMessageData", {})
    url = fm.get("downloadUrl")
    if not url:
        return None
    return url, fm.get("fileName") or "audio.ogg"


@app.post("/webhook/green-api")
async def webhook(request: Request):
    body = await request.json()

    tw = body.get("typeWebhook")
    if tw != "incomingMessageReceived":
        print(f"[webhook] skip: typeWebhook={tw}")
        return {"ok": True, "skipped": "not an incoming message"}

    id_message = body.get("idMessage", "")
    if database.already_processed(id_message):
        print(f"[webhook] skip: duplicate {id_message}")
        return {"ok": True, "skipped": "duplicate"}

    sender_data = body.get("senderData") or body.get("sender_data") or {}
    chat_id = sender_data.get("chatId", "")
    sender = (sender_data.get("sender") or sender_data.get("chatId") or "").split("@")[0]
    message_data = body.get("messageData", {})
    print(
        f"[webhook] in: sender={sender} chat={chat_id} "
        f"type={message_data.get('typeMessage')} whitelist={_WHITELIST}"
    )

    if chat_id.endswith("@g.us") and not _ANSWER_GROUPS:
        return {"ok": True, "skipped": "group"}

    if sender not in _WHITELIST:
        print(f"[webhook] skip: {sender} not in whitelist")
        return {"ok": True, "skipped": "not whitelisted"}

    text = _extract_text(message_data)

    if not text:
        audio = _extract_audio_url(message_data)
        if audio:
            url, fname = audio
            try:
                transcribed = transcribe(download_file(url), fname)
            except Exception as e:  # noqa: BLE001
                transcribed = None
                print(f"[webhook] audio download failed: {e}")
            if transcribed:
                text = f"[הודעה קולית] {transcribed}"
            else:
                send_reply(
                    chat_id,
                    "קיבלתי הודעה קולית אבל לא הצלחתי לתמלל אותה מלך. תשלח שוב או תכתוב לי?",
                )
                return {"ok": True, "handled": "audio-untranscribed"}

    if not text:
        print(f"[webhook] skip: unsupported type {message_data.get('typeMessage')}")
        return {"ok": True, "skipped": f"unsupported type {message_data.get('typeMessage')}"}

    print(f"[webhook] handling: {text[:80]!r}")
    try:
        reply = agent.handle_message(chat_id, sender, text)
    except Exception as e:  # noqa: BLE001
        print(f"[webhook] agent error: {e}")
        reply = "סליחה מלך, נתקלתי בתקלה. תנסה שוב עוד רגע 👑"

    send_reply(chat_id, reply)
    return {"ok": True}
