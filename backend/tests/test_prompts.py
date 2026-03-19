from __future__ import annotations

from backend.services.chat_memory import RetrievedMemory
from backend.services.conversation_state import CompletedTurn
from backend.services.prompts import SYSTEM_PROMPT, MatchedAppContext, build_user_prompt


def test_build_user_prompt_without_background():
    prompt = build_user_prompt(
        "How are you?",
        user_name="Test User",
        is_first_turn=True,
    )

    assert "### CONTEXT" in prompt
    assert "- first_turn: true" in prompt
    assert "- user_name: Test User" in prompt
    assert "### RELEVANT BACKGROUND" not in prompt
    assert "### RECENT CONVERSATION" in prompt
    assert "(none)" in prompt
    assert "### CURRENT USER QUERY" in prompt
    assert "How are you?" in prompt


def test_build_user_prompt_with_app_context_and_memory():
    prompt = build_user_prompt(
        "What should I do next?",
        user_name="Test User",
        matched_app=MatchedAppContext(
            app_id="tux_paint",
            name="Tux Paint",
            description="A simple and creative drawing program.",
            score=0.88,
            start_step="Open Tux Paint from the menu.",
        ),
        retrieved_background=[
            RetrievedMemory(
                document="User: I need a drawing app\nAssistant: Tux Paint is simple.",
                score=0.91,
                timestamp="2026-03-15T12:00:00+00:00",
                turn_index=1,
            )
        ],
        recent_turns=[
            CompletedTurn(
                user_text="Can it help beginners?",
                assistant_text="Yes, it is simple for beginners.",
            )
        ],
    )

    assert "- matched_app_name: Tux Paint" in prompt
    assert "- matched_app_description: A simple and creative drawing program." in prompt
    assert "- matched_app_start_step: Open Tux Paint from the menu." in prompt
    assert "### RELEVANT BACKGROUND" in prompt
    assert "Memory 1 (score=0.910):" in prompt
    assert "### RECENT CONVERSATION" in prompt
    assert "Turn 1 User: Can it help beginners?" in prompt
    assert "### CURRENT USER QUERY" in prompt


def test_build_user_prompt_with_conversation_summary():
    prompt = build_user_prompt(
        "What should I learn next?",
        user_name="Test User",
        conversation_summary="The learner is practicing addition and wants simple examples.",
    )

    assert "### CONVERSATION SUMMARY" in prompt
    assert "The learner is practicing addition" in prompt


def test_system_prompt_keeps_neutral_low_resource_guidance():
    assert "practical learning and support assistant" in SYSTEM_PROMPT
    assert "Use simple English only." in SYSTEM_PROMPT
    assert "Act like a patient tutor." in SYSTEM_PROMPT
    assert "Prefer low-cost, low-tech, practical suggestions." in SYSTEM_PROMPT
    assert 'end with a short section titled "Related app"' in SYSTEM_PROMPT
    assert "Do not invent, substitute, or recommend any outside app, website, platform, or service." in SYSTEM_PROMPT
    assert "If no app context is provided, do not mention any app, website, software, or external learning platform at all." in SYSTEM_PROMPT
    assert "Do not ask the user to choose between learning modes." in SYSTEM_PROMPT
