from __future__ import annotations

import os
import subprocess
import sys

from backend.services.conversation_state import CompletedTurn


def test_generate_hidden_summary_uses_shared_default_model(monkeypatch):
    import backend.services.assistant as assistant

    captured = {}

    def _fake_generate_response(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "fifty-word summary placeholder"

    monkeypatch.setattr(assistant, "generate_response", _fake_generate_response)

    result = assistant.generate_hidden_summary(
        [
            CompletedTurn(
                user_text="I need help studying.",
                assistant_text="Let us make a simple plan.",
            )
        ]
    )

    assert result == "fifty-word summary placeholder"
    assert "exactly 50 words" in captured["prompt"]
    assert captured["kwargs"]["system"] == assistant.SUMMARY_SYSTEM_PROMPT
    assert captured["kwargs"]["timeout"] == 120
    assert "model" not in captured["kwargs"]


def test_default_model_uses_gpt_oss_when_env_not_set(monkeypatch):
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


def test_default_model_respects_llama_cpp_model_alias_env(monkeypatch):
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
