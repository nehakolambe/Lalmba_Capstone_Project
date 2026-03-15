from __future__ import annotations

import logging

from backend.models import Conversation
from backend.services.app_manifest import AppManifestEntry
from backend.services.app_search import AppMatch


def _register_and_login(client, payload):
    client.post("/auth/register", json=payload)
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": payload["username"], "pin": payload["pin"]})


def test_chat_requires_authentication(client):
    response = client.post("/chat/message", json={"text": "Hello"})
    data = response.get_json()
    assert response.status_code == 401
    assert data["error"] == "Authentication required"


def test_chat_rejects_empty_message(client, registered_user_payload):
    _register_and_login(client, registered_user_payload)
    response = client.post("/chat/message", json={"text": "   "})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Message text is required"


def test_chat_message_history_and_reset(client, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    monkeypatch.setattr(
        "backend.routes.chat.search_apps",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Mocked assistant reply",
    )

    message_response = client.post("/chat/message", json={"text": "How are you?"})
    message_data = message_response.get_json()

    assert message_response.status_code == 201
    assert len(message_data["messages"]) == 2
    assert message_data["messages"][0]["role"] == "user"
    assert message_data["messages"][1]["role"] == "assistant"
    assert message_data["messages"][1]["content"] == "Mocked assistant reply"
    assert message_data["summary_checkpoint_ran"] is False

    conversation = Conversation.query.filter_by(user_id=1).first()
    assert conversation is not None
    assert conversation.turns_since_last_summary == 1
    assert conversation.current_summary is None

    history_response = client.get("/chat/history?limit=1")
    history_data = history_response.get_json()
    assert history_response.status_code == 200
    assert len(history_data["history"]) == 1
    assert history_data["history"][0]["role"] == "assistant"

    reset_response = client.post("/chat/reset")
    assert reset_response.status_code == 200

    post_reset_history = client.get("/chat/history")
    post_reset_data = post_reset_history.get_json()
    assert post_reset_history.status_code == 200
    assert post_reset_data["history"] == []
    assert Conversation.query.filter_by(user_id=1).first() is None


def test_chat_message_passes_matched_app_context(client, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    app_match = AppMatch(
        app=AppManifestEntry(
            app_id="tux_paint",
            name="Tux Paint",
            description="A drawing app for kids and beginners.",
            tutorial_steps=("Open it",),
        ),
        score=0.91,
    )
    captured = {}

    monkeypatch.setattr(
        "backend.routes.chat.search_apps",
        lambda *_args, **_kwargs: app_match,
    )

    def _fake_reply(message_text, **kwargs):
        captured["message_text"] = message_text
        captured["kwargs"] = kwargs
        return "You can try drawing by hand. Tux Paint is also on your other device."

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "Is there a drawing app?"})

    assert response.status_code == 201
    assert captured["message_text"] == "Is there a drawing app?"
    assert captured["kwargs"]["matched_app"] is not None
    assert captured["kwargs"]["matched_app"].app_id == "tux_paint"
    assert captured["kwargs"]["matched_app"].name == "Tux Paint"
    assert captured["kwargs"]["matched_app"].description == "A drawing app for kids and beginners."


def test_chat_message_uses_no_app_context_when_no_match(client, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    captured = {}

    monkeypatch.setattr(
        "backend.routes.chat.search_apps",
        lambda *_args, **_kwargs: None,
    )

    def _fake_reply(message_text, **kwargs):
        captured["message_text"] = message_text
        captured["kwargs"] = kwargs
        return "Mocked assistant reply"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "How are you?"})

    assert response.status_code == 201
    assert captured["message_text"] == "How are you?"
    assert captured["kwargs"]["matched_app"] is None


def test_chat_message_falls_back_when_app_search_fails(client, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    captured = {}

    def _raise_search_error(*_args, **_kwargs):
        raise RuntimeError("search is unavailable")

    def _fake_reply(message_text, **kwargs):
        captured["message_text"] = message_text
        captured["kwargs"] = kwargs
        return "Mocked assistant reply"

    monkeypatch.setattr("backend.routes.chat.search_apps", _raise_search_error)
    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "Is there a drawing app?"})

    assert response.status_code == 201
    assert captured["message_text"] == "Is there a drawing app?"
    assert captured["kwargs"]["matched_app"] is None


def test_chat_message_triggers_summary_checkpoint_before_sixth_turn(
    client, registered_user_payload, monkeypatch, caplog
):
    _register_and_login(client, registered_user_payload)

    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda message_text, **kwargs: f"Reply to: {message_text}",
    )

    for index in range(5):
        response = client.post("/chat/message", json={"text": f"Question {index + 1}"})
        assert response.status_code == 201

    captured = {}

    def _fake_summary(turns):
        captured["turns"] = turns
        return "fifty-word summary placeholder"

    monkeypatch.setattr("backend.routes.chat.generate_hidden_summary", _fake_summary)

    with caplog.at_level(logging.INFO, logger="backend.routes.chat"):
        response = client.post("/chat/message", json={"text": "Question 6"})
    data = response.get_json()

    assert response.status_code == 201
    assert data["summary_checkpoint_ran"] is True
    assert len(captured["turns"]) == 5
    assert captured["turns"][0].user_text == "Question 1"
    assert captured["turns"][-1].assistant_text == "Reply to: Question 5"
    assert "Generated hidden summary for user 1: fifty-word summary placeholder" in caplog.text

    conversation = Conversation.query.filter_by(user_id=1).first()
    assert conversation.current_summary == "fifty-word summary placeholder"
    assert conversation.turns_since_last_summary == 1


def test_chat_message_blocks_when_summary_generation_fails(
    client, registered_user_payload, monkeypatch, caplog
):
    _register_and_login(client, registered_user_payload)

    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda message_text, **kwargs: f"Reply to: {message_text}",
    )

    for index in range(5):
        response = client.post("/chat/message", json={"text": f"Question {index + 1}"})
        assert response.status_code == 201

    conversation = Conversation.query.filter_by(user_id=1).first()
    assert conversation.turns_since_last_summary == 5

    def _raise_summary_error(_turns):
        from backend.services.llama_cpp_client import LlamaCppError

        raise LlamaCppError("summary failed", reason="boom")

    monkeypatch.setattr("backend.routes.chat.generate_hidden_summary", _raise_summary_error)

    with caplog.at_level(logging.INFO, logger="backend.routes.chat"):
        response = client.post("/chat/message", json={"text": "Question 6"})
    data = response.get_json()

    assert response.status_code == 503
    assert "conversation memory" in data["error"]
    assert Conversation.query.filter_by(user_id=1).first().turns_since_last_summary == 5
    assert "Generated hidden summary for user 1:" not in caplog.text
