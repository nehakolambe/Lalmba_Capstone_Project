from __future__ import annotations

import logging
import os
import subprocess
import sys

from backend.services.chat_memory import RetrievedMemory
from backend.services.conversation_state import CompletedTurn


def test_generate_assistant_reply_logs_prompt_metadata(monkeypatch, caplog):
    import backend.services.assistant as assistant

    captured = {}

    def _fake_generate_response(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "Helpful reply"

    monkeypatch.setattr(assistant, "generate_response", _fake_generate_response)

    with caplog.at_level(logging.INFO, logger="backend.services.assistant"):
        result = assistant.generate_assistant_reply(
            "What should I do next?",
            user_name="Test User",
            user_id=7,
            conversation_summary="Learner needs a next step.",
            retrieved_background=[
                RetrievedMemory(
                    document="User: I need help\nAssistant: Start small.",
                    score=0.84,
                    timestamp="2026-03-15T12:00:00+00:00",
                    turn_index=1,
                )
            ],
            recent_turns=[
                CompletedTurn(
                    user_text="I feel stuck.",
                    assistant_text="Let us try one easy step.",
                )
            ],
            prompt_log={
                "chroma_matches": 3,
                "threshold_matches": 2,
                "budget_matches": 1,
                "background_chars": 42,
            },
        )

    assert result == "Helpful reply"
    assert captured["kwargs"]["system"] == assistant.SYSTEM_PROMPT
    assert captured["kwargs"]["timeout"] == 120
    assert "### RELEVANT BACKGROUND" in captured["prompt"]
    assert "Prompt constructed user_id=7" in caplog.text
    assert "chroma_matches=3" in caplog.text
    assert "budget_matches=1" in caplog.text
    assert "summary_chars=" in caplog.text


def test_generate_assistant_reply_logs_full_prompts_when_enabled(app, monkeypatch, caplog):
    import backend.services.assistant as assistant

    def _fake_generate_response(prompt, **kwargs):
        return "Helpful reply"

    monkeypatch.setattr(assistant, "generate_response", _fake_generate_response)

    app.config["LOG_FULL_PROMPTS"] = True
    with app.app_context():
        with caplog.at_level(logging.INFO, logger="backend.services.assistant"):
            assistant.generate_assistant_reply(
                "Teach me addition",
                user_name="Neha",
                user_id=1,
            )

    assert "Full system prompt:" in caplog.text
    assert "Full user prompt:" in caplog.text
    assert "### CURRENT USER QUERY\nTeach me addition" in caplog.text


def test_generate_conversation_summary_uses_llm(monkeypatch):
    import backend.services.assistant as assistant

    captured = {}

    def _fake_generate_response(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "Short summary"

    monkeypatch.setattr(assistant, "generate_response", _fake_generate_response)

    result = assistant.generate_conversation_summary(
        "Earlier summary",
        [
            CompletedTurn(
                user_text="Teach me subtraction",
                assistant_text="Start with taking away small numbers.",
            )
        ],
    )

    assert result == "Short summary"
    assert captured["kwargs"]["system"] == assistant.SUMMARY_SYSTEM_PROMPT
    assert "### PREVIOUS SUMMARY" in captured["prompt"]


def test_default_model_uses_local_model_when_env_not_set():
    env = os.environ.copy()
    env.pop("LLAMA_CPP_MODEL_ALIAS", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import backend.services.llama_cpp_client as module; print(module.DEFAULT_MODEL)",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.stdout.strip() == "local-model"


def test_default_model_respects_llama_cpp_model_alias_env():
    env = os.environ.copy()
    env["LLAMA_CPP_MODEL_ALIAS"] = "custom-model"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import backend.services.llama_cpp_client as module; print(module.DEFAULT_MODEL)",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.stdout.strip() == "custom-model"
