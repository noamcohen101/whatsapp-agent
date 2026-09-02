"""LLM call + tool-calling loop (Google Gemini). One entry point: handle_message()."""
from google import genai
from google.genai import types

import database
from config import GEMINI_API_KEY, LLM_MODEL, LLM_VISION_MODEL, SPEC
from prompt import build_system_prompt
from tools import TOOL_REGISTRY

_client = genai.Client(api_key=GEMINI_API_KEY)
_MAX_TOOL_ITERS = 6

# In a group chat the bot is a shared assistant — only these tools are exposed.
_GROUP_ALLOWED_TOOLS = {
    "web_search", "fetch_page", "youtube_transcript", "compare_competitor_prices",
    "woo_orders_overview", "woo_list_orders", "woo_get_order",
    "woo_list_products", "woo_get_product", "woo_sales_summary", "woo_list_customers",
}

FRAMEWORK_INJECTED_CHAT_ID = {"create_reminder", "list_reminders", "cancel_reminder"}

_AUDITED = {
    "create_calendar_event", "update_calendar_event", "delete_calendar_event",
    "send_email", "create_email_draft",
    "woo_update_product", "woo_create_product", "woo_duplicate_product", "woo_create_coupon",
    "create_reminder", "cancel_reminder",
    "add_task", "update_task", "remember", "forget", "link_shipment", "log_decision",
}

_READ_ONLY_SAFE = {
    "set_safety_state", "get_safety_state", "list_standing_approvals",
    "list_tasks", "list_memories", "list_decisions", "list_experiments",
    "what_i_did", "llm_cost", "revenue_pace", "profit_analysis", "growth_snapshot",
    "customer_segments", "scan_subscriptions",
}


def _active_tools(context: str) -> dict:
    if context == "group":
        return {k: v for k, v in TOOL_REGISTRY.items() if k in _GROUP_ALLOWED_TOOLS}
    return TOOL_REGISTRY


def _clean_schema(node):
    """Anthropic input_schema -> Gemini-friendly OpenAPI subset."""
    if not isinstance(node, dict):
        return node
    out = {}
    for k, v in node.items():
        if k in ("additionalProperties", "$schema", "title", "default"):
            continue
        if k == "properties" and isinstance(v, dict):
            out["properties"] = {pk: _clean_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out["items"] = _clean_schema(v)
        else:
            out[k] = v
    return out


def _gemini_tools(registry: dict):
    decls = []
    for td in registry.values():
        s = td["schema"]
        params = _clean_schema(s.get("input_schema", {"type": "object", "properties": {}}))
        if not params.get("properties"):
            params = None
        decls.append(
            types.FunctionDeclaration(
                name=s["name"], description=s.get("description", ""), parameters=params
            )
        )
    return [types.Tool(function_declarations=decls)] if decls else None


def _run_tool(name, tool_input, chat_id, registry, context="private") -> str:
    if name not in registry:
        return f"[שגיאה] הכלי '{name}' לא זמין בהקשר הזה."
    state = database.setting_get("safety_state", "normal")
    if state == "paused":
        return "[הבוט במצב מושהה] תגיד 'חזור לפעילות' כדי להפעיל."
    if state == "read_only" and name in _AUDITED and name not in _READ_ONLY_SAFE:
        return f"[מצב קריאה בלבד] לא מבצע את {name}. תגיד 'חזור לפעילות'."
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
    chat_id, sender_phone, message_text,
    images=None, context="private", sender_name="", cheap_model=False,
) -> str:
    registry = _active_tools(context)
    memories = database.all_memories() if context != "group" else None
    open_tasks = database.task_list("open") if context != "group" else None
    settings = None
    if context != "group":
        settings = database.settings_all()
        appr = database.approval_list()
        if appr:
            settings["_standing_approvals"] = "\n".join(f"- {a['rule']}" for a in appr)

    system_prompt = build_system_prompt(
        SPEC, registry, context=context, memories=memories,
        open_tasks=open_tasks, settings=settings,
    )

    # history -> Gemini contents
    contents = []
    for m in database.tail(chat_id):
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    if context == "group" and sender_name:
        message_text = f"[{sender_name}]: {message_text}"

    user_parts = []
    if images:
        import base64
        for mt, data in images:
            user_parts.append(types.Part.from_bytes(data=base64.b64decode(data), mime_type=mt))
    user_parts.append(types.Part(text=message_text or "מה יש בתמונה?"))
    contents.append(types.Content(role="user", parts=user_parts))

    model = LLM_VISION_MODEL if images else LLM_MODEL
    cfg = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=_gemini_tools(registry),
        temperature=0.7,
        max_output_tokens=2500,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    reply_text = ""
    for _ in range(_MAX_TOOL_ITERS):
        resp = _client.models.generate_content(model=model, contents=contents, config=cfg)
        try:
            u = resp.usage_metadata
            database.usage_log(model, u.prompt_token_count or 0, u.candidates_token_count or 0)
        except Exception:  # noqa: BLE001
            pass

        cand = resp.candidates[0] if resp.candidates else None
        parts = cand.content.parts if cand and cand.content and cand.content.parts else []
        calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        texts = [p.text for p in parts if getattr(p, "text", None)]
        if texts:
            reply_text = "\n".join(texts).strip()

        if not calls:
            break

        contents.append(cand.content)
        tool_parts = []
        for fc in calls:
            out = _run_tool(fc.name, dict(fc.args or {}), chat_id, registry, context)
            tool_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": out})
            )
        contents.append(types.Content(role="user", parts=tool_parts))
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
