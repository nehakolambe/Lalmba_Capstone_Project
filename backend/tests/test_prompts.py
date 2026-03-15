from __future__ import annotations

from backend.services.conversation_state import CompletedTurn
from backend.services.prompts import (
    MatchedAppContext,
    SUMMARY_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_summary_prompt,
    build_user_prompt,
)


def test_build_user_prompt_without_app_context():
    prompt = build_user_prompt(
        "How are you?",
        user_name="Test User",
        is_first_turn=True,
    )

    assert "- first_turn: true" in prompt
    assert "- user_name: Test User" in prompt
    assert "- matched_app_name:" not in prompt
    assert "- matched_app_description:" not in prompt
    assert "Instruction priority for this turn:" in prompt
    assert "Follow the current user message first." in prompt
    assert "Current user message:\nHow are you?" in prompt


def test_build_user_prompt_with_app_context():
    prompt = build_user_prompt(
        "Is there a drawing app?",
        user_name="Test User",
        is_first_turn=False,
        matched_app=MatchedAppContext(
            app_id="tux_paint",
            name="Tux Paint",
            description="A simple and creative drawing program.",
            score=0.88,
        ),
    )

    assert "- matched_app_name: Tux Paint" in prompt
    assert "- matched_app_description: A simple and creative drawing program." in prompt
    assert "tutorial_steps" not in prompt
    assert "0.88" not in prompt


def test_build_user_prompt_with_summary_overlap_and_recent_turns():
    prompt = build_user_prompt(
        "What should I try next?",
        user_name="Test User",
        current_summary="The user wants a drawing app for practice.",
        overlap_turns=[
            CompletedTurn(
                user_text="Is there a drawing app?",
                assistant_text="Yes, Tux Paint is available.",
            )
        ],
        recent_turns=[
            CompletedTurn(
                user_text="Can it help beginners?",
                assistant_text="Yes, it is simple for beginners.",
            )
        ],
    )

    assert "Conversation summary:\nThe user wants a drawing app for practice." in prompt
    assert "Overlap context:" in prompt
    assert "Turn 1 User: Is there a drawing app?" in prompt
    assert "Turn 1 Assistant: Yes, Tux Paint is available." in prompt
    assert "Recent conversation:" in prompt
    assert "Turn 1 User: Can it help beginners?" in prompt
    assert "Current user message:\nWhat should I try next?" in prompt


def test_build_summary_prompt_and_system_prompt_focus_on_50_words_and_apps():
    prompt = build_summary_prompt(
        [
            CompletedTurn(
                user_text="I need help choosing a drawing app.",
                assistant_text="Tux Paint is a simple option.",
            )
        ]
    )

    assert "exactly 50 words" in prompt
    assert "current goal, active preferences, pending next step, and any apps discussed" in prompt
    assert "Conversation:" in prompt
    assert "Turn 1 User: I need help choosing a drawing app." in prompt
    assert "exactly 50 words" in SUMMARY_SYSTEM_PROMPT


def test_system_prompt_describes_brief_app_mention_behavior():
    assert "answer the user's question first" in SYSTEM_PROMPT
    assert "mention the app in one short sentence" in SYSTEM_PROMPT
    assert "other device" in SYSTEM_PROMPT
    assert "Do not turn the reply into an app recommendation" in SYSTEM_PROMPT


def test_system_prompt_removes_named_persona_and_keeps_neutral_assistant_role():
    assert "You are Mama Akinyi" not in SYSTEM_PROMPT
    assert "if asked your name, say Mama Akinyi" not in SYSTEM_PROMPT
    assert "You are a practical learning and support assistant." in SYSTEM_PROMPT
    assert "do not present yourself as a named person or character" in SYSTEM_PROMPT


def test_system_prompt_keeps_broad_low_resource_constraints():
    assert "limited access to electricity, internet, media, transport, and expensive tools" in SYSTEM_PROMPT
    assert "Prefer low-cost, low-tech, locally practical suggestions." in SYSTEM_PROMPT
    assert "Avoid relying on infrastructure-heavy solutions unless the user explicitly confirms access." in SYSTEM_PROMPT


def test_system_prompt_prioritizes_latest_instruction_and_language_preference():
    assert "Reply in simple, clear English by default." in SYSTEM_PROMPT
    assert "Stay in English unless the user explicitly asks to switch languages." in SYSTEM_PROMPT
    assert "keep replying only in English until they explicitly change that preference" in SYSTEM_PROMPT
    assert "Do not infer a language switch from tone, prior assistant replies, partial non-English text, or older context." in SYSTEM_PROMPT
    assert "Follow the user's latest direct instruction and current topic over older plans or examples." in SYSTEM_PROMPT
    assert "If the user asks to be tested before the next lesson, do the test first." in SYSTEM_PROMPT
