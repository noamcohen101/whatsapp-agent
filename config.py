"""Loads .env and spec.json, exposes settings. Fails fast on missing config."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"חסר משתנה סביבה חובה: {name}. בדוק את קובץ .env (או את ההגדרות ב-Render)."
        )
    return val


# --- Green API ---
GREEN_API_URL = _require("GREEN_API_URL").rstrip("/")
GREEN_API_INSTANCE = _require("GREEN_API_INSTANCE")
GREEN_API_TOKEN = _require("GREEN_API_TOKEN")

# --- LLM ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
# Sonnet — strong Hebrew + reasoning. Worth the extra cost for a personal assistant.
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5")
LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "claude-sonnet-4-5")
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# --- Transcription (voice messages) ---
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_TRANSCRIBE_MODEL = os.getenv("GROQ_TRANSCRIBE_MODEL", "whisper-large-v3-turbo")

# --- Google (Calendar + Gmail) ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")

# --- WooCommerce (Israstore) ---
WOO_URL = os.getenv("WOO_URL", "").rstrip("/")
WOO_KEY = os.getenv("WOO_KEY", "")
WOO_SECRET = os.getenv("WOO_SECRET", "")

# --- Bot ---
BOT_OWNER_PHONE = _require("BOT_OWNER_PHONE").lstrip("+")
BOT_TIMEZONE = os.getenv("BOT_TIMEZONE", "Asia/Jerusalem")

# --- Storage (Postgres via Supabase session pooler) ---
DATABASE_URL = _require("DATABASE_URL")

MAX_HISTORY = int(os.getenv("MAX_HISTORY", "30"))

APP_VERSION = 1

# --- Spec (source of truth for behavior) ---
with open(BASE_DIR / "spec.json", encoding="utf-8") as f:
    SPEC = json.load(f)
