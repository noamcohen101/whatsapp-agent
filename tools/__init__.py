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

# --- Google Calendar ---
if "google_calendar" in SPEC.get("tools", []):
    from tools.google_calendar import TOOLS as _calendar_tools

    _register(_calendar_tools)

# --- External tools are added here by wa-connect, e.g.:
# from tools.gmail import TOOLS as _gmail_tools
# _register(_gmail_tools)
