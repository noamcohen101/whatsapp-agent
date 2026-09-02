"""Voice-message transcription via Groq Whisper. Falls back gracefully."""
import io

from config import GROQ_API_KEY, GROQ_TRANSCRIBE_MODEL, TRANSCRIPTION_PROVIDER


_MAX_BYTES = 24 * 1024 * 1024  # Groq API limit ~25MB


def transcribe(
    audio_bytes: bytes, filename: str = "audio.ogg", language: str | None = "he"
) -> str | None:
    """Return transcription text, or None if unavailable/failed."""
    if TRANSCRIPTION_PROVIDER != "groq" or not GROQ_API_KEY:
        return None
    if len(audio_bytes) > _MAX_BYTES:
        print(f"[transcription] file too large: {len(audio_bytes)} bytes")
        return "__TOO_LARGE__"
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        buf = io.BytesIO(audio_bytes)
        buf.name = filename
        kwargs = dict(file=buf, model=GROQ_TRANSCRIBE_MODEL, response_format="text")
        if language:
            kwargs["language"] = language
        result = client.audio.transcriptions.create(**kwargs)
        text = result if isinstance(result, str) else getattr(result, "text", "")
        return (text or "").strip() or None
    except Exception as e:  # noqa: BLE001 - transcription is best-effort
        print(f"[transcription] failed: {e}")
        return None
