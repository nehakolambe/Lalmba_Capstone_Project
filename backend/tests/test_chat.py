from __future__ import annotations


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
