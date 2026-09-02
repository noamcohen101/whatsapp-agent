"""TOOL_REGISTRY: name -> {"schema": <Anthropic tool schema>, "fn": <callable>}.

Starts with native tools only. wa-connect appends external tools (calendar, gmail, ...).
"""
from config import SPEC

TOOL_REGISTRY: dict[str, dict] = {}


def _register(tools: dict) -> None:
    TOOL_REGISTRY.update(tools)


# --- Reminders (native, no external auth) ---
if "reminders" in SPEC.get("tools", []):
    from tools.reminders import TOOLS as _reminder_tools

    _register(_reminder_tools)

# --- Semantic memory (always on) ---
from tools.memory import TOOLS as _memory_tools

_register(_memory_tools)

# --- Task Layer (always on) ---
from tools.tasks import TOOLS as _task_tools

_register(_task_tools)

# --- Audit trail + decision journal (always on) ---
from tools.journal import TOOLS as _journal_tools

_register(_journal_tools)

# --- YouTube transcript / summary (always on) ---
from tools.youtube import TOOLS as _youtube_tools

_register(_youtube_tools)

# --- Audio / podcast transcription from URL (always on) ---
from tools.audio_transcribe import TOOLS as _audio_tools

_register(_audio_tools)

# --- Google Calendar ---
if "google_calendar" in SPEC.get("tools", []):
    from tools.google_calendar import TOOLS as _calendar_tools

    _register(_calendar_tools)

# --- Gmail (read-only) ---
if "gmail" in SPEC.get("tools", []):
    from tools.gmail import TOOLS as _gmail_tools

    _register(_gmail_tools)

# --- Web search (keyless) ---
if "web_search" in SPEC.get("tools", []):
    from tools.web_search import TOOLS as _web_tools

    _register(_web_tools)

# --- WooCommerce (Israstore) ---
if "woocommerce" in SPEC.get("tools", []):
    from tools.woocommerce import TOOLS as _woo_tools

    _register(_woo_tools)

# --- WhatsApp group reading ---
if "whatsapp_groups" in SPEC.get("tools", []):
    from tools.whatsapp_groups import TOOLS as _group_tools

    _register(_group_tools)

# --- Competitor price intelligence ---
if "woocommerce" in SPEC.get("tools", []):
    from tools.competitors import TOOLS as _competitor_tools

    _register(_competitor_tools)

# --- Shipment tracking ---
if "woocommerce" in SPEC.get("tools", []):
    from tools.shipments import TOOLS as _shipment_tools

    _register(_shipment_tools)
