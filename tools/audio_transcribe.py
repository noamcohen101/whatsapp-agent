"""Transcribe a podcast / audio file from a direct URL."""
import httpx

from transcription import transcribe


def transcribe_audio_url(url: str) -> str:
    try:
        r = httpx.get(url, timeout=90, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        return f"[שגיאה בהורדת האודיו] {e}"
    ctype = r.headers.get("content-type", "")
    if "audio" not in ctype and not url.lower().endswith(
        (".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac")
    ):
        return "הקישור הזה לא נראה כמו קובץ אודיו ישיר. צריך לינק שמפנה ישירות לקובץ mp3/m4a."
    name = url.split("/")[-1].split("?")[0] or "audio.mp3"
    text = transcribe(r.content, name, language=None)  # auto-detect language
    if text == "__TOO_LARGE__":
        return (
            "הקובץ גדול מדי לתמלול בבת אחת (מעל ~24MB). "
            "אם זה פודקאסט ארוך — שלח לי קישור יוטיוב שלו, או קובץ קצר יותר."
        )
    if not text:
        return "לא הצלחתי לתמלל את האודיו."
    return text[:40000]


TOOLS = {
    "transcribe_audio_url": {
        "schema": {
            "name": "transcribe_audio_url",
            "description": (
                "מתמלל קובץ אודיו / פודקאסט מקישור ישיר (mp3/m4a). "
                "לסרטוני יוטיוב השתמש ב-youtube_transcript. עד ~24MB."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "קישור ישיר לקובץ האודיו"}},
                "required": ["url"],
            },
        },
        "fn": transcribe_audio_url,
    }
}
