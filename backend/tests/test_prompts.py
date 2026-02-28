from __future__ import annotations

from backend.services.prompts import MatchedAppContext, SYSTEM_PROMPT, build_user_prompt


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
    assert "User message:\nHow are you?" in prompt


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


def test_system_prompt_describes_brief_app_mention_behavior():
    assert "answer the user's question first" in SYSTEM_PROMPT
    assert "briefly mention the app" in SYSTEM_PROMPT
    assert "other device" in SYSTEM_PROMPT
    assert "do not give step-by-step app instructions yet" in SYSTEM_PROMPT
