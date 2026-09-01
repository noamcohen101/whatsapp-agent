"""Voice-message transcription via Groq Whisper. Falls back gracefully."""
import io

from config import GROQ_API_KEY, GROQ_TRANSCRIBE_MODEL, TRANSCRIPTION_PROVIDER


def transcribe(audio_bytes: bytes, filename: str = "audio.ogg") -> str | None:
    """Return Hebrew transcription text, or None if transcription is unavailable/failed."""
    if TRANSCRIPTION_PROVIDER != "groq" or not GROQ_API_KEY:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        buf = io.BytesIO(audio_bytes)
        buf.name = filename
        result = client.audio.transcriptions.create(
            file=buf,
            model=GROQ_TRANSCRIBE_MODEL,
            language="he",
            response_format="text",
        )
        text = result if isinstance(result, str) else getattr(result, "text", "")
        return (text or "").strip() or None
    except Exception as e:  # noqa: BLE001 - transcription is best-effort
        print(f"[transcription] failed: {e}")
        return None
