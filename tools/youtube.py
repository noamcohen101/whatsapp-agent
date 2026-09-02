"""Summarize a YouTube video from its transcript (captions)."""
import re

_ID_RE = re.compile(
    r"(?:youtu\.be/|watch\?v=|/embed/|/shorts/|/live/)([A-Za-z0-9_-]{11})"
)

_MAX_CHARS = 40000  # ~1.5h of speech; plenty for Sonnet


def _video_id(url: str) -> str | None:
    m = _ID_RE.search(url)
    if m:
        return m.group(1)
    url = url.strip()
    return url if re.fullmatch(r"[A-Za-z0-9_-]{11}", url) else None


def youtube_transcript(url: str) -> str:
    vid = _video_id(url)
    if not vid:
        return "לא זיהיתי קישור יוטיוב תקין."
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        try:
            fetched = api.fetch(vid, languages=["he", "en"])
        except Exception:
            # any available language
            tlist = api.list(vid)
            tr = next(iter(tlist))
            fetched = tr.fetch()
        text = " ".join(seg.text for seg in fetched if seg.text.strip())
    except Exception as e:  # noqa: BLE001
        return f"[אין תמלול זמין לסרטון הזה] {type(e).__name__}"
    if not text.strip():
        return "[הסרטון בלי כתוביות — אי אפשר לתמלל]"
    return text[:_MAX_CHARS]


TOOLS = {
    "youtube_transcript": {
        "schema": {
            "name": "youtube_transcript",
            "description": (
                "מביא את התמלול המלא של סרטון יוטיוב לפי קישור, כדי שתוכל לסכם אותו / "
                "להוציא נקודות מפתח / לזהות מה רלוונטי ל-Israstore. עובד רק אם לסרטון יש כתוביות."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "קישור לסרטון יוטיוב"}},
                "required": ["url"],
            },
        },
        "fn": youtube_transcript,
    }
}
