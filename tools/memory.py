"""Durable semantic memory — facts the bot learns about Noam and the business."""
import database


def remember(content: str, category: str = "general") -> str:
    mid = database.add_memory(content.strip(), category.strip() or "general")
    return f"נשמר בזיכרון (#{mid}): {content}"


def list_memories() -> str:
    rows = database.all_memories()
    if not rows:
        return "עוד אין לי שום דבר שמור בזיכרון הקבוע."
    by_cat: dict[str, list[str]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(f"#{r['id']} {r['content']}")
    out = []
    for cat, items in by_cat.items():
        out.append(f"**{cat}**")
        out.extend(f"  - {i}" for i in items)
    return "\n".join(out)


def forget(memory_id: int) -> str:
    return "נמחק מהזיכרון." if database.delete_memory(int(memory_id)) else "לא מצאתי זיכרון עם המספר הזה."


TOOLS = {
    "remember": {
        "schema": {
            "name": "remember",
            "description": (
                "שומר עובדה קבועה בזיכרון ארוך-הטווח. השתמש כשנועם אומר לך משהו שכדאי לזכור "
                "לתמיד — העדפה, כלל, פרט על העסק, החלטה עקרונית, פרט על אדם חשוב. "
                "אל תשמור מידע רגעי או משהו שכבר בזיכרון. "
                "קטגוריות: preferences, business, people, rules, personal, "
                "voice_style (איך נועם אוהב שכותבים), insight (תובנות ורעיונות ששווה לזכור), "
                "energy_pattern (מתי נועם חד/גמור), general."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "העובדה, קצר וברור"},
                    "category": {"type": "string", "description": "קטגוריה"},
                },
                "required": ["content"],
            },
        },
        "fn": remember,
    },
    "list_memories": {
        "schema": {
            "name": "list_memories",
            "description": "מציג את כל מה ששמור בזיכרון הקבוע. השתמש כשנועם שואל 'מה אתה זוכר'.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "fn": list_memories,
    },
    "forget": {
        "schema": {
            "name": "forget",
            "description": "מוחק עובדה מהזיכרון הקבוע לפי המספר שלה. השתמש כשנועם אומר 'תשכח את זה'.",
            "input_schema": {
                "type": "object",
                "properties": {"memory_id": {"type": "integer", "description": "מספר הזיכרון"}},
                "required": ["memory_id"],
            },
        },
        "fn": forget,
    },
}
