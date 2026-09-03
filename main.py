"""FastAPI app: Green API webhook -> agent -> reply."""
import base64
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request

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

_GROUP_CFG = SPEC.get("tools_config", {}).get("whatsapp_groups", {})
_ALLOWED_GROUPS = {
    g["chat_id"]
    for g in _GROUP_CFG.get("allowed_groups", [])
    if _GROUP_CFG.get("respond_in_group")
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    if "reminders" in SPEC.get("tools", []):
        from tools.reminders import scheduler, start_scheduler

        start_scheduler()
        import automations

        automations.register(scheduler)
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


_VISION_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _extract_images(message_data: dict) -> list[tuple[str, str]]:
    """Return [(media_type, base64_data)] for an incoming image message, else []."""
    if message_data.get("typeMessage") not in ("imageMessage", "stickerMessage"):
        return []
    fm = message_data.get("fileMessageData", {})
    url = fm.get("downloadUrl")
    if not url:
        return []
    media_type = (fm.get("mimeType") or "image/jpeg").split(";")[0].strip()
    if media_type not in _VISION_TYPES:
        media_type = "image/jpeg"
    try:
        raw = download_file(url)
    except Exception as e:  # noqa: BLE001
        print(f"[webhook] image download failed: {e}")
        return []
    if len(raw) > 4_500_000:  # Anthropic ~5MB/image cap, leave headroom
        print("[webhook] image too large, skipping")
        return []
    return [(media_type, base64.b64encode(raw).decode())]


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
async def webhook(request: Request, bg: BackgroundTasks):
    body = await request.json()
    if body.get("typeWebhook") == "incomingMessageReceived":
        # Heavy work (transcribe, LLM, tool calls) runs off the event loop
        # so /health and other requests are never blocked.
        bg.add_task(_handle, body)
    return {"ok": True}


def _handle(body: dict) -> None:
    id_message = body.get("idMessage", "")
    if database.already_processed(id_message):
        print(f"[webhook] skip: duplicate {id_message}")
        return

    sender_data = body.get("senderData") or body.get("sender_data") or {}
    chat_id = sender_data.get("chatId", "")
    sender = (sender_data.get("sender") or sender_data.get("chatId") or "").split("@")[0]
    message_data = body.get("messageData", {})
    print(
        f"[webhook] in: sender={sender} chat={chat_id} "
        f"type={message_data.get('typeMessage')} whitelist={_WHITELIST}"
    )

    is_group = chat_id.endswith("@g.us")
    if is_group:
        if chat_id not in _ALLOWED_GROUPS:
            database.mark_processed(id_message)
            return
        context = "group"
    else:
        if sender not in _WHITELIST:
            print(f"[webhook] skip: {sender} not in whitelist")
            database.mark_processed(id_message)
            return
        context = "private"

    sender_name = sender_data.get("senderName") or sender_data.get("chatName") or ""

    text = _extract_text(message_data)
    images = _extract_images(message_data)

    if not text and message_data.get("typeMessage") == "documentMessage":
        fm = message_data.get("fileMessageData", {})
        url = fm.get("downloadUrl")
        fname = fm.get("fileName") or "document"
        caption = fm.get("caption", "")
        mime = fm.get("mimeType", "")
        is_audio = "audio" in mime or fname.lower().endswith(
            (".mp3", ".m4a", ".wav", ".ogg", ".aac")
        )
        if url and is_audio:
            try:
                transcribed = transcribe(download_file(url), fname, language=None)
            except Exception as e:  # noqa: BLE001
                transcribed = None
                print(f"[webhook] audio-doc transcription failed: {e}")
            if transcribed == "__TOO_LARGE__":
                send_reply(chat_id, "הקובץ ארוך מדי לתמלול בבת אחת (מעל ~24MB). שלח קצר יותר או קישור יוטיוב.")
                return
            if transcribed:
                text = f"[תמלול אודיו: {fname}]\n{transcribed}\n\n{caption}".strip()
            else:
                send_reply(chat_id, f"קיבלתי את '{fname}' אבל לא הצלחתי לתמלל אותו.")
                return
        elif url:
            try:
                import documents

                extracted = documents.extract(download_file(url), fname, mime)
            except Exception as e:  # noqa: BLE001
                extracted = None
                print(f"[webhook] document handling failed: {e}")
            if extracted:
                text = f"[מסמך: {fname}]\n{extracted}\n\n{caption}".strip()
            else:
                send_reply(
                    chat_id,
                    f"קיבלתי את הקובץ '{fname}' אבל לא הצלחתי לקרוא אותו מלך. "
                    "אני יודע לקרוא PDF, Excel, Word, CSV וטקסט.",
                )
                return

    if images:
        caption = message_data.get("fileMessageData", {}).get("caption", "")
        try:
            reply = agent.handle_message(
                chat_id, sender, text or caption, images=images,
                context=context, sender_name=sender_name,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[webhook] agent error (image): {e}")
            reply = "סליחה מלך, נתקלתי בתקלה בניתוח התמונה. תנסה שוב 👑"
        send_reply(chat_id, reply)
        database.mark_processed(id_message)
        return

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
                database.mark_processed(id_message)
                return

    if not text:
        print(f"[webhook] skip: unsupported type {message_data.get('typeMessage')}")
        database.mark_processed(id_message)
        return

    print(f"[webhook] handling ({context}): {text[:80]!r}")
    try:
        reply = agent.handle_message(
            chat_id, sender, text, context=context, sender_name=sender_name
        )
    except Exception as e:  # noqa: BLE001
        print(f"[webhook] agent error: {e}")
        reply = "סליחה מלך, נתקלתי בתקלה. תנסה שוב עוד רגע 👑"

    send_reply(chat_id, reply)
    database.mark_processed(id_message)
    return
