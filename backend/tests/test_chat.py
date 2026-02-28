from __future__ import annotations

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
