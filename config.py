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
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5")
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# --- Transcription (voice messages) ---
TRANSCRIPTION_PROVIDER = os.getenv("TRANSCRIPTION_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_TRANSCRIBE_MODEL = os.getenv("GROQ_TRANSCRIBE_MODEL", "whisper-large-v3-turbo")

# --- Bot ---
BOT_OWNER_PHONE = _require("BOT_OWNER_PHONE").lstrip("+")
BOT_TIMEZONE = os.getenv("BOT_TIMEZONE", "Asia/Jerusalem")

# --- Storage ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/conversations.db")
_db_abs = (BASE_DIR / DATABASE_PATH).resolve()
_db_abs.parent.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = str(_db_abs)

MAX_HISTORY = int(os.getenv("MAX_HISTORY", "30"))

APP_VERSION = 1

# --- Spec (source of truth for behavior) ---
with open(BASE_DIR / "spec.json", encoding="utf-8") as f:
    SPEC = json.load(f)
