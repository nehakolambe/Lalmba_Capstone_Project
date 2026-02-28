from __future__ import annotations

import logging

from .ollama_client import OllamaError, generate_response
from .prompts import (
    SUMMARY_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    MatchedAppContext,
    build_summary_prompt,
    build_user_prompt,
)
from .conversation_state import CompletedTurn

logger = logging.getLogger(__name__)


def generate_assistant_reply(
    user_text: str,
    user_name: str | None = None,
    is_first_turn: bool = False,
    matched_app: MatchedAppContext | None = None,
    current_summary: str | None = None,
    overlap_turns: list[CompletedTurn] | None = None,
    recent_turns: list[CompletedTurn] | None = None,
    fallback_on_error: bool = False,
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
        matched_app=matched_app,
        current_summary=current_summary,
        overlap_turns=overlap_turns,
        recent_turns=recent_turns,
    )

    try:
        return generate_response(
            user_prompt,
            system=SYSTEM_PROMPT,
            timeout=120,  # first call can be slow if model is cold
        )

    except OllamaError as e:
        logger.exception("Ollama failed: %s (reason=%s status=%s)", e, getattr(e, "reason", None), getattr(e, "status", None))
        if not fallback_on_error:
            raise
        return "I’m having trouble reaching the local AI model right now. Please try again in a moment."


def generate_hidden_summary(turns: list[CompletedTurn]) -> str:
    """Generate a hidden rolling summary for the previous 5 completed turns."""
    return generate_response(
        build_summary_prompt(turns),
        system=SUMMARY_SYSTEM_PROMPT,
        model="llama3.2:3b",
        timeout=120,
    )
