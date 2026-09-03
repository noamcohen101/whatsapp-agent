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

# --- Projects: chief-of-staff for what Noam is building (always on) ---
from tools.projects import TOOLS as _project_tools

_register(_project_tools)

# --- Idea vault + build progress log (always on) ---
from tools.ideas import TOOLS as _idea_tools

_register(_idea_tools)

# --- Audit trail + decision journal (always on) ---
from tools.journal import TOOLS as _journal_tools

_register(_journal_tools)

# --- A/B experiment tracker (always on) ---
from tools.experiments import TOOLS as _experiment_tools

_register(_experiment_tools)

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

# --- Growth: revenue pace + customer segments ---
if "woocommerce" in SPEC.get("tools", []):
    from tools.growth import TOOLS as _growth_tools

    _register(_growth_tools)

# --- Subscription / recurring-charge watch ---
if "gmail" in SPEC.get("tools", []):
    from tools.subscriptions import TOOLS as _sub_tools

    _register(_sub_tools)

# --- LLM cost report (always on) ---
from tools.cost import TOOLS as _cost_tools

_register(_cost_tools)

# --- Control: safety state + standing approvals (always on) ---
from tools.control import TOOLS as _control_tools

_register(_control_tools)

# --- Profit intelligence + growth strategy ---
if "woocommerce" in SPEC.get("tools", []):
    from tools.profit import TOOLS as _profit_tools
    from tools.strategy import TOOLS as _strategy_tools

    _register(_profit_tools)
    _register(_strategy_tools)
