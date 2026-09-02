"""LLM call + tool-calling loop (Anthropic). One entry point: handle_message()."""
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_VISION_MODEL, SPEC
import database
from prompt import build_system_prompt
from tools import TOOL_REGISTRY

_client = Anthropic(api_key=ANTHROPIC_API_KEY)
_MAX_TOOL_ITERS = 5

# In a group chat the bot is a shared assistant — only these tools are exposed.
# Everything personal to Noam (calendar, gmail, personal reminders) and every
# write action (woo_update_product, woo_create_coupon) is hidden.
_GROUP_ALLOWED_TOOLS = {
    "web_search",
    "fetch_page",
    "youtube_transcript",
    "compare_competitor_prices",
    "woo_orders_overview",
    "woo_list_orders",
    "woo_get_order",
    "woo_list_products",
    "woo_get_product",
    "woo_sales_summary",
    "woo_list_customers",
}

# Parameters the framework owns — the LLM never gets to choose these.
FRAMEWORK_INJECTED_CHAT_ID = {
    "create_reminder",
    "list_reminders",
    "cancel_reminder",
    # wa-connect appends here when human_handoff is added
}


def _active_tools(context: str) -> dict:
    if context == "group":
        return {k: v for k, v in TOOL_REGISTRY.items() if k in _GROUP_ALLOWED_TOOLS}
    return TOOL_REGISTRY


def _anthropic_tools(registry: dict) -> list[dict]:
    return [td["schema"] for td in registry.values()]


# tools that change something in the world / durable state — worth auditing
_AUDITED = {
    "create_calendar_event", "update_calendar_event", "delete_calendar_event",
    "send_email", "create_email_draft",
    "woo_update_product", "woo_create_product", "woo_duplicate_product", "woo_create_coupon",
    "create_reminder", "cancel_reminder",
    "add_task", "update_task", "remember", "forget", "link_shipment",
    "log_decision",
}


def _run_tool(name: str, tool_input: dict, chat_id: str, registry: dict, context: str = "private") -> str:
    if name not in registry:
        return f"[שגיאה] הכלי '{name}' לא זמין בהקשר הזה."
    args = dict(tool_input or {})
    if name in FRAMEWORK_INJECTED_CHAT_ID:
        args["chat_id"] = chat_id
    try:
        result = str(registry[name]["fn"](**args))
        if name in _AUDITED:
            summary = ", ".join(f"{k}={v}" for k, v in args.items() if k != "chat_id")
            database.audit_log(name, f"{summary} → {result[:200]}", context)
        return result
    except Exception as e:  # noqa: BLE001
        return f"[שגיאה בהרצת {name}] {e}"


def handle_message(
    chat_id: str,
    sender_phone: str,
    message_text: str,
    images: list[tuple[str, str]] | None = None,
    context: str = "private",
    sender_name: str = "",
    cheap_model: bool = False,
) -> str:
    """images: list of (media_type, base64_data) for vision. context: 'private' | 'group'."""
    registry = _active_tools(context)
    memories = database.all_memories() if context != "group" else None
    open_tasks = database.task_list("open") if context != "group" else None
    settings = database.settings_all() if context != "group" else None
    system_prompt = build_system_prompt(
        SPEC, registry, context=context, memories=memories,
        open_tasks=open_tasks, settings=settings,
    )

    history = database.tail(chat_id)
    messages: list[dict] = [{"role": m["role"], "content": m["content"]} for m in history]

    if context == "group" and sender_name:
        message_text = f"[{sender_name}]: {message_text}"

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

    if images:
        model = LLM_VISION_MODEL
    elif cheap_model:
        model = "claude-haiku-4-5"
    else:
        model = LLM_MODEL
    max_tokens = 2000 if images else 1024

    reply_text = ""
    for _ in range(_MAX_TOOL_ITERS):
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        tools = _anthropic_tools(registry)
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
            out = _run_tool(tu.name, tu.input, chat_id, registry, context)
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
