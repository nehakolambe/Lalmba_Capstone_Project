from __future__ import annotations

import logging
from typing import Optional

from .ollama_client import OllamaError, generate_response

logger = logging.getLogger(__name__)




def generate_assistant_reply(user_text: str, user_name: str | None = None) -> str:
    """Simple placeholder reply logic for local development."""
    cleaned = (user_text or "").strip()
    name = (user_name or "").strip() or "there"

    if not cleaned:
        return f"Hello {name}! What would you like to chat about today?"

    lower = cleaned.lower()

    prompt = (
        f"{lower} Answer this question in two sentences."
    )

    print(prompt)
    # print(generate_response(prompt))

    try:
        return generate_response(
            prompt,
            timeout=120,  # first call can be slow if model is cold
        )

    except OllamaError as e:
        logger.exception("Ollama failed: %s (reason=%s status=%s)", e, getattr(e, "reason", None), getattr(e, "status", None))
        return "I’m having trouble reaching the local AI model right now. Please try again in a moment."


    print("You try to get the output by now")


    # lower = cleaned.lower()
    # if any(greeting in lower for greeting in ("hello", "hi", "habari", "hey")):
    #     return f"Hello {name}! How can I support you today?"
    # if "help" in lower:
    #     return (
    #         "I'm here to help. Share a little more about what you're working on, and we can tackle it together."
    #     )

    return f"You said: {cleaned}"
