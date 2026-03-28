from __future__ import annotations

from backend.services.chat_memory import RetrievedMemory
from backend.services.conversation_state import CompletedTurn
from backend.services.prompts import (
    SYSTEM_PROMPT,
    MatchedAppContext,
    UserProfileContext,
    build_user_prompt,
)


def test_build_user_prompt_without_background():
    prompt = build_user_prompt(
        "How are you?",
        user_name="Test User",
        is_first_turn=True,
    )

    assert "### CONTEXT" in prompt
    assert "- first_turn: true" in prompt
    assert "- user_name: Test User" in prompt
    assert "### USER PROFILE" not in prompt
    assert "### RELEVANT BACKGROUND" not in prompt
    assert "### RECENT CONVERSATION" in prompt
    assert "(none)" in prompt
    assert "### CURRENT USER QUERY" in prompt
    assert "How are you?" in prompt


def test_build_user_prompt_with_user_profile():
    prompt = build_user_prompt(
        "Explain fractions",
        user_name="Test User",
        user_profile=UserProfileContext(
            age_group="teen",
            education_level="class_7",
            preferred_language="english",
            english_fluency="beginner",
            computer_literacy="intermediate",
        ),
    )

    assert "### USER PROFILE" in prompt
    assert "- age_group: teen" in prompt
    assert "- education_level: class_7" in prompt
    assert "- preferred_language: english" in prompt
    assert "- english_fluency: beginner" in prompt
    assert "- computer_literacy: intermediate" in prompt


def test_build_user_prompt_omits_english_fluency_for_kiswahili_profile():
    prompt = build_user_prompt(
        "Nisaidie",
        user_name="Test User",
        user_profile=UserProfileContext(
            age_group="adult",
            education_level="adult",
            preferred_language="kiswahili",
            english_fluency=None,
            computer_literacy="beginner",
        ),
    )

    assert "- preferred_language: kiswahili" in prompt
    assert "english_fluency" not in prompt


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


def test_system_prompt_keeps_profile_guidance():
    assert "practical learning assistant" in SYSTEM_PROMPT
    assert "Reply in the user's preferred language by default." in SYSTEM_PROMPT
    assert "age group, education level, English fluency, and computer literacy" in SYSTEM_PROMPT
