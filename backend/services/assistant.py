from __future__ import annotations

import logging

from .ollama_client import OllamaError, generate_response
from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

def generate_assistant_reply(
    user_text: str,
    user_name: str | None = None,
    is_first_turn: bool = False,
) -> str:
    """Generate an assistant reply using separate system and user prompts."""
    cleaned = (user_text or "").strip()
    name = (user_name or "").strip() or "there"

    if not cleaned:
        return f"Hello {name}! What would you like to chat about today?"

    user_prompt = build_user_prompt(
        cleaned,
        user_name=user_name,
        is_first_turn=is_first_turn,
    )

    try:
        return generate_response(
            user_prompt,
            system=SYSTEM_PROMPT,
            timeout=120,  # first call can be slow if model is cold
        )

    except OllamaError as e:
        logger.exception("Ollama failed: %s (reason=%s status=%s)", e, getattr(e, "reason", None), getattr(e, "status", None))
        return "I’m having trouble reaching the local AI model right now. Please try again in a moment."
