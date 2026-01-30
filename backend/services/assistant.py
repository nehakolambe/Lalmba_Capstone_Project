from __future__ import annotations


def generate_assistant_reply(user_text: str, user_name: str | None = None) -> str:
    """Simple placeholder reply logic for local development."""
    cleaned = (user_text or "").strip()
    name = (user_name or "").strip() or "there"

    if not cleaned:
        return f"Hello {name}! What would you like to chat about today?"

    lower = cleaned.lower()
    if any(greeting in lower for greeting in ("hello", "hi", "habari", "hey")):
        return f"Hello {name}! How can I support you today?"
    if "help" in lower:
        return (
            "I'm here to help. Share a little more about what you're working on, and we can tackle it together."
        )

    return f"You said: {cleaned}"
