"""LLM call + tool-calling loop (Anthropic). One entry point: handle_message()."""
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, LLM_MODEL, SPEC
import database
from prompt import build_system_prompt
from tools import TOOL_REGISTRY

_client = Anthropic(api_key=ANTHROPIC_API_KEY)
_MAX_TOOL_ITERS = 5

# Parameters the framework owns — the LLM never gets to choose these.
FRAMEWORK_INJECTED_CHAT_ID = {
    "create_reminder",
    "list_reminders",
    "cancel_reminder",
    # wa-connect appends here when human_handoff is added
}


def _anthropic_tools() -> list[dict]:
    return [td["schema"] for td in TOOL_REGISTRY.values()]


def _run_tool(name: str, tool_input: dict, chat_id: str) -> str:
    if name not in TOOL_REGISTRY:
        return f"[שגיאה] הכלי '{name}' לא קיים."
    args = dict(tool_input or {})
    if name in FRAMEWORK_INJECTED_CHAT_ID:
        args["chat_id"] = chat_id
    try:
        result = TOOL_REGISTRY[name]["fn"](**args)
        return str(result)
    except Exception as e:  # noqa: BLE001
        return f"[שגיאה בהרצת {name}] {e}"


def handle_message(
    chat_id: str,
    sender_phone: str,
    message_text: str,
    images: list[tuple[str, str]] | None = None,
) -> str:
    """images: list of (media_type, base64_data) for vision, e.g. ('image/jpeg', '...')."""
    system_prompt = build_system_prompt(SPEC, TOOL_REGISTRY)

    history = database.tail(chat_id)
    messages: list[dict] = [{"role": m["role"], "content": m["content"]} for m in history]

    if images:
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mt, "data": data},
            }
            for mt, data in images
        ]
        content.append({"type": "text", "text": message_text or "מה יש בתמונה?"})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": message_text})

    reply_text = ""
    for _ in range(_MAX_TOOL_ITERS):
        kwargs = dict(
            model=LLM_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        tools = _anthropic_tools()
        if tools:
            kwargs["tools"] = tools

        resp = _client.messages.create(**kwargs)

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        text_blocks = [b.text for b in resp.content if b.type == "text"]
        if text_blocks:
            reply_text = "\n".join(text_blocks).strip()

        if resp.stop_reason != "tool_use" or not tool_uses:
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for tu in tool_uses:
            out = _run_tool(tu.name, tu.input, chat_id)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tu.id, "content": out}
            )
        messages.append({"role": "user", "content": tool_results})
    else:
        if not reply_text:
            reply_text = "סליחה מלך, הסתבכתי עם הבקשה הזאת. תנסה לנסח אחרת?"

    if not reply_text:
        reply_text = "קיבלתי 👑"

    stored = message_text
    if images:
        stored = f"[שלח {len(images)} תמונה/ות] {message_text}".strip()
    database.append(chat_id, "user", stored)
    database.append(chat_id, "assistant", reply_text)
    return reply_text
