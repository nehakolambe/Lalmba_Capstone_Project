from __future__ import annotations

import json

from backend.models import ChatThread, Message
from backend.services.app_manifest import AppManifestEntry
from backend.services.app_search import AppMatch


def _register_and_login(client, payload):
    client.post("/auth/register", json=payload)
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": payload["username"], "pin": payload["pin"]})


class FakeChatMemory:
    def __init__(self, retrieval=None, archive_error=None):
        self.retrieval = retrieval
        self.archive_error = archive_error
        self.appended = []
        self.archived = []
        self.deleted = []
        self.cleared = []

    def retrieve_context(self, user_id, thread_id, query_text):
        self.last_retrieve = (user_id, thread_id, query_text)
        return self.retrieval

    def archive_turn(self, *, user_id, thread_id, query_text, response_text, timestamp=None):
        if self.archive_error is not None:
            raise self.archive_error
        self.archived.append((user_id, thread_id, query_text, response_text))
        return f"user-{user_id}-thread-{thread_id}-turn-{len(self.archived)}"

    def delete_archive_doc(self, doc_id):
        self.deleted.append(doc_id)

    def append_recent_turn(self, user_id, thread_id, query_text, response_text):
        self.appended.append((user_id, thread_id, query_text, response_text))

    def clear_user(self, user_id):
        self.cleared.append(user_id)

    def clear_thread(self, user_id, thread_id):
        self.cleared.append((user_id, thread_id))


class FakeAppIndex:
    def __init__(self, entries):
        self.entries = tuple(entries)


def _stub_auto_title(monkeypatch, title="Topic"):
    monkeypatch.setattr(
        "backend.routes.chat.build_auto_thread_title",
        lambda _message_text: title,
    )


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


def test_chat_message_history_and_reset(client, app, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory

    _stub_auto_title(monkeypatch, title="How are you")
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Mocked assistant reply",
    )

    message_response = client.post("/chat/message", json={"text": "How are you?"})
    message_data = message_response.get_json()

    assert message_response.status_code == 201
    assert len(message_data["messages"]) == 2
    assert message_data["thread"]["title"] == "How are you"
    assert message_data["session"]["question_count"] == 1
    assert message_data["session"]["questions_remaining"] == 9
    assert fake_memory.archived == [(1, 1, "How are you?", "Mocked assistant reply")]
    assert fake_memory.appended == [(1, 1, "How are you?", "Mocked assistant reply")]

    history_response = client.get("/chat/history?limit=1")
    history_data = history_response.get_json()
    assert history_response.status_code == 200
    assert len(history_data["history"]) == 1
    assert history_data["history"][0]["role"] == "assistant"
    assert history_data["session"]["question_count"] == 1

    reset_response = client.post("/chat/reset")
    assert reset_response.status_code == 200
    assert fake_memory.cleared == [(1, 1)]

    post_reset_history = client.get("/chat/history")
    post_reset_data = post_reset_history.get_json()
    assert post_reset_history.status_code == 200
    assert post_reset_data["history"] == []
    assert post_reset_data["session"]["question_count"] == 0


def test_chat_first_question_auto_generates_short_thread_title(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory

    _stub_auto_title(monkeypatch, title="What is fire?")
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Fire is heat, light, and gases from burning.",
    )

    response = client.post("/chat/message", json={"text": "What is fire?"})
    data = response.get_json()

    assert response.status_code == 201
    assert data["thread"]["title"] == "What is fire?"

    threads_response = client.get("/chat/threads")
    threads_data = threads_response.get_json()
    assert threads_response.status_code == 200
    assert threads_data["threads"][0]["title"] == "What is fire?"


def test_chat_auto_title_runs_only_for_first_message(client, app, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory
    title_calls = []

    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)

    def _fake_build_title(message_text):
        title_calls.append(message_text)
        return message_text

    monkeypatch.setattr("backend.routes.chat.build_auto_thread_title", _fake_build_title)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Reply",
    )

    first = client.post("/chat/message", json={"text": "What is fire?"})
    second = client.post("/chat/message", json={"text": "Why is it hot?"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert title_calls == ["What is fire?"]


def test_chat_manual_rename_is_not_overwritten_by_later_messages(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory

    _stub_auto_title(monkeypatch, title="What is fire?")
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Reply",
    )

    first = client.post("/chat/message", json={"text": "What is fire?"})
    thread_id = first.get_json()["thread"]["id"]
    renamed = client.patch(f"/chat/threads/{thread_id}", json={"title": "Science notes"})
    second = client.post("/chat/message", json={"thread_id": thread_id, "text": "Why is it hot?"})

    assert first.status_code == 201
    assert renamed.status_code == 200
    assert second.status_code == 201
    assert second.get_json()["thread"]["title"] == "Science notes"


def test_chat_message_passes_app_context_without_blocking(client, app, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    _stub_auto_title(monkeypatch)
    app_match = AppMatch(
        app=AppManifestEntry(
            app_id="tux_paint",
            name="Tux Paint",
            description="A drawing app for kids and beginners.",
            tutorial_steps=("Open it",),
        ),
        score=0.91,
    )
    app.extensions["app_search_index"] = FakeAppIndex([app_match.app])
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: app_match)

    captured = {}

    def _fake_reply(message_text, **kwargs):
        captured["message_text"] = message_text
        captured["kwargs"] = kwargs
        return "You can start drawing with simple shapes.\n\nRelated app: Tux Paint"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "Teach me drawing basics"})
    data = response.get_json()

    assert response.status_code == 201
    assert "simple shapes" in data["messages"][1]["content"]
    assert captured["kwargs"]["matched_app"] is not None
    assert captured["kwargs"]["matched_app"].app_id == "tux_paint"
    conversation = ChatThread.query.filter_by(user_id=1).first()
    assert conversation.last_suggested_app_id == "tux_paint"
    assert conversation.last_app_topic_hint == "drawing-art"


def test_chat_message_suppresses_repeated_same_app_suggestion(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    _stub_auto_title(monkeypatch)
    app_match = AppMatch(
        app=AppManifestEntry(
            app_id="tux_math",
            name="Tux of Math Command",
            description="A math game for practice.",
            tutorial_steps=("Open Tux Math",),
        ),
        score=0.91,
    )
    captured = {}

    app.extensions["app_search_index"] = FakeAppIndex([app_match.app])
    _stub_auto_title(monkeypatch)

    def _search(_app, query, **_kwargs):
        if "math" in query.lower():
            return app_match
        return None

    monkeypatch.setattr("backend.routes.chat.search_apps", _search)

    def _fake_reply(message_text, **kwargs):
        captured["message_text"] = message_text
        captured.setdefault("matched_apps", []).append(kwargs["matched_app"])
        return "Tutor reply"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    first_response = client.post("/chat/message", json={"text": "Teach me math addition"})
    second_response = client.post("/chat/message", json={"text": "Test my math subtraction skills"})

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert captured["matched_apps"][0] is not None
    assert captured["matched_apps"][0].app_id == "tux_math"
    assert captured["matched_apps"][1] is None


def test_chat_message_allows_repeat_when_user_explicitly_asks_for_app(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    _stub_auto_title(monkeypatch)
    app_match = AppMatch(
        app=AppManifestEntry(
            app_id="tux_math",
            name="Tux of Math Command",
            description="A math game for practice.",
            tutorial_steps=("Open Tux Math",),
        ),
        score=0.91,
    )
    captured = {"matched_apps": []}

    app.extensions["app_search_index"] = FakeAppIndex([app_match.app])

    def _search(_app, query, **_kwargs):
        if "math" in query.lower():
            return app_match
        return None

    monkeypatch.setattr("backend.routes.chat.search_apps", _search)

    def _fake_reply(_message_text, **kwargs):
        captured["matched_apps"].append(kwargs["matched_app"])
        return "Tutor reply"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    first = client.post("/chat/message", json={"text": "Teach me maths"})
    second = client.post("/chat/message", json={"text": "Is there a math app I can use?"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert captured["matched_apps"][0] is not None
    assert captured["matched_apps"][1] is not None


def test_chat_message_does_not_surface_app_for_unrelated_followup(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    app_match = AppMatch(
        app=AppManifestEntry(
            app_id="tux_math",
            name="Tux of Math Command",
            description="A math game for practice.",
            tutorial_steps=("Open Tux Math",),
        ),
        score=0.91,
    )
    captured = {}

    app.extensions["app_search_index"] = FakeAppIndex([app_match.app])

    def _search(_app, query, **_kwargs):
        if "math" in query.lower():
            return app_match
        return None

    monkeypatch.setattr("backend.routes.chat.search_apps", _search)

    def _fake_reply(message_text, **kwargs):
        captured["message_text"] = message_text
        captured["matched_app"] = kwargs["matched_app"]
        return "Tutor reply"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "Tell me a story about a penguin"})

    assert response.status_code == 201
    assert captured["matched_app"] is None


def test_chat_message_falls_back_when_app_search_fails(client, app, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    _stub_auto_title(monkeypatch)
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
    assert captured["kwargs"]["matched_app"] is None


def test_chat_message_passes_retrieved_memory_to_prompt_builder(
    client, app, registered_user_payload, monkeypatch
):
    from backend.services.chat_memory import MemoryRetrievalResult, RetrievedMemory
    from backend.services.conversation_state import CompletedTurn

    _register_and_login(client, registered_user_payload)

    retrieval = MemoryRetrievalResult(
        recent_turns=[CompletedTurn(user_text="Hi", assistant_text="Hello")],
        matches_returned=3,
        matches_after_threshold=2,
        matches_after_budget=1,
        background_chars=32,
        anchors=[
            RetrievedMemory(
                document="User: Hi\nAssistant: Hello",
                score=0.91,
                timestamp="2026-03-15T12:00:00+00:00",
                turn_index=1,
            )
        ],
    )
    fake_memory = FakeChatMemory(retrieval=retrieval)
    app.extensions["chat_memory"] = fake_memory
    captured = {}

    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)

    def _fake_reply(message_text, **kwargs):
        captured["kwargs"] = kwargs
        return "Reply"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "What now?"})

    assert response.status_code == 201
    assert fake_memory.last_retrieve == (1, 1, "What now?")
    assert len(captured["kwargs"]["retrieved_background"]) == 1
    assert len(captured["kwargs"]["recent_turns"]) == 1
    assert captured["kwargs"]["conversation_summary"] is None
    assert captured["kwargs"]["prompt_log"]["chroma_matches"] == 3
    assert captured["kwargs"]["prompt_log"]["budget_matches"] == 1


def test_chat_message_passes_user_profile_context(client, app, registered_user_payload, monkeypatch):
    client.post("/auth/register", json=registered_user_payload)
    client.patch(
        "/auth/profile",
        json={
            "age_group": "teen",
            "education_level": "class_8",
            "preferred_language": "english",
            "english_fluency": "beginner",
            "computer_literacy": "beginner",
        },
    )

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    captured = {}

    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)

    def _fake_reply(message_text, **kwargs):
        captured["kwargs"] = kwargs
        return "Reply"

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _fake_reply)

    response = client.post("/chat/message", json={"text": "Teach me division"})

    assert response.status_code == 201
    assert captured["kwargs"]["user_profile"] is not None
    assert captured["kwargs"]["user_profile"].education_level == "class_8"
    assert captured["kwargs"]["user_profile"].english_fluency == "beginner"


def test_chat_enforces_question_limit(client, app, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Reply",
    )

    for index in range(10):
        response = client.post("/chat/message", json={"text": f"Question {index}"})
        assert response.status_code == 201

    blocked = client.post("/chat/message", json={"text": "Question 11"})
    blocked_data = blocked.get_json()

    assert blocked.status_code == 200
    assert len(blocked_data["messages"]) == 1
    assert "10-question limit" in blocked_data["messages"][0]["content"]
    assert blocked_data["session"]["limit_reached"] is True
    assert Message.query.filter_by(role="user").count() == 10


def test_chat_message_returns_503_and_writes_no_memory_on_llm_failure(
    client, app, registered_user_payload, monkeypatch
):
    from backend.services.llama_cpp_client import LlamaCppError

    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory

    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)

    def _raise_llm_error(*_args, **_kwargs):
        raise LlamaCppError("boom", reason="down")

    monkeypatch.setattr("backend.routes.chat.generate_assistant_reply", _raise_llm_error)

    response = client.post("/chat/message", json={"text": "Question"})
    data = response.get_json()

    assert response.status_code == 503
    assert "local AI model" in data["error"]
    assert fake_memory.archived == []
    assert fake_memory.appended == []
    assert Message.query.count() == 0


def test_chat_message_rolls_back_archive_when_sql_commit_fails(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Reply",
    )

    original_commit = app.extensions["sqlalchemy"].session.commit

    def _fail_once():
        app.extensions["sqlalchemy"].session.commit = original_commit
        raise RuntimeError("db down")

    app.extensions["sqlalchemy"].session.commit = _fail_once

    response = client.post("/chat/message", json={"text": "Question"})

    assert response.status_code == 503
    assert fake_memory.deleted == ["user-1-thread-1-turn-1"]
    assert fake_memory.appended == []


def test_chat_threads_do_not_share_memory_context(
    client, app, registered_user_payload, monkeypatch
):
    from backend.services.chat_memory import MemoryRetrievalResult

    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(
        retrieval=MemoryRetrievalResult(
            recent_turns=[],
            matches_returned=0,
            matches_after_threshold=0,
            matches_after_budget=0,
            background_chars=0,
            anchors=[],
        )
    )
    app.extensions["chat_memory"] = fake_memory
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda message_text, **_kwargs: f"Reply to {message_text}",
    )

    first = client.post("/chat/message", json={"text": "i want to learn paint"})
    assert first.status_code == 201

    thread_response = client.post("/chat/threads", json={})
    thread_id = thread_response.get_json()["thread"]["id"]

    second = client.post(
        "/chat/message",
        json={"thread_id": thread_id, "text": "what is rain?"},
    )

    assert second.status_code == 201
    assert fake_memory.archived == [
        (1, 1, "i want to learn paint", "Reply to i want to learn paint"),
        (1, thread_id, "what is rain?", "Reply to what is rain?"),
    ]
    assert fake_memory.last_retrieve == (1, thread_id, "what is rain?")


def test_chat_updates_summary_after_summary_window(client, app, registered_user_payload, monkeypatch):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    app.config["CHAT_SUMMARY_WINDOW_TURNS"] = 2
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda message_text, **_kwargs: f"Reply to {message_text}",
    )
    monkeypatch.setattr(
        "backend.routes.chat.generate_conversation_summary",
        lambda previous_summary, turns: f"Summary of {len(turns)} turns",
    )

    client.post("/chat/message", json={"text": "First lesson"})
    response = client.post("/chat/message", json={"text": "Second lesson"})

    conversation = ChatThread.query.filter_by(user_id=1).first()

    assert response.status_code == 201
    assert conversation.current_summary == "Summary of 2 turns"
    assert conversation.turns_since_last_summary == 0


def test_chat_message_stream_emits_deltas_and_persists_exchange(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.stream_assistant_reply",
        lambda *_args, **_kwargs: iter(["Hello", " there"]),
    )

    response = client.post("/chat/message/stream", json={"text": "Hi"}, buffered=True)

    assert response.status_code == 200
    assert response.mimetype == "application/x-ndjson"

    events = [
        json.loads(line)
        for line in response.get_data(as_text=True).splitlines()
        if line.strip()
    ]

    assert events[0] == {"type": "delta", "content": "Hello"}
    assert events[1] == {"type": "delta", "content": " there"}
    assert events[2]["type"] == "done"
    assert events[2]["message"]["content"] == "Hello there"
    assert events[2]["session"]["question_count"] == 1
    assert fake_memory.archived == [(1, 1, "Hi", "Hello there")]
    assert fake_memory.appended == [(1, 1, "Hi", "Hello there")]


def test_chat_message_stream_returns_json_when_question_limit_reached(
    client, app, registered_user_payload, monkeypatch
):
    _register_and_login(client, registered_user_payload)

    app.extensions["chat_memory"] = FakeChatMemory(retrieval=None)
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "backend.routes.chat.generate_assistant_reply",
        lambda *_args, **_kwargs: "Reply",
    )

    for index in range(10):
        response = client.post("/chat/message", json={"text": f"Question {index}"})
        assert response.status_code == 201

    blocked = client.post("/chat/message/stream", json={"text": "Question 11"})
    blocked_data = blocked.get_json()

    assert blocked.status_code == 200
    assert "10-question limit" in blocked_data["messages"][0]["content"]
    assert blocked_data["session"]["limit_reached"] is True


def test_chat_message_stream_returns_503_before_first_chunk_on_llm_failure(
    client, app, registered_user_payload, monkeypatch
):
    from backend.services.llama_cpp_client import LlamaCppError

    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)

    def _raise_stream_error(*_args, **_kwargs):
        raise LlamaCppError("boom", reason="down")
        yield

    monkeypatch.setattr("backend.routes.chat.stream_assistant_reply", _raise_stream_error)

    response = client.post("/chat/message/stream", json={"text": "Question"})
    data = response.get_json()

    assert response.status_code == 503
    assert "local AI model" in data["error"]
    assert fake_memory.archived == []
    assert fake_memory.appended == []
    assert Message.query.count() == 0


def test_chat_message_stream_emits_error_event_and_skips_persistence_on_midstream_failure(
    client, app, registered_user_payload, monkeypatch
):
    from backend.services.llama_cpp_client import LlamaCppError

    _register_and_login(client, registered_user_payload)

    fake_memory = FakeChatMemory(retrieval=None)
    app.extensions["chat_memory"] = fake_memory
    _stub_auto_title(monkeypatch)
    monkeypatch.setattr("backend.routes.chat.search_apps", lambda *_args, **_kwargs: None)

    def _failing_stream(*_args, **_kwargs):
        yield "Hello"
        raise LlamaCppError("boom", reason="down")

    monkeypatch.setattr("backend.routes.chat.stream_assistant_reply", _failing_stream)

    response = client.post("/chat/message/stream", json={"text": "Question"}, buffered=True)
    events = [
        json.loads(line)
        for line in response.get_data(as_text=True).splitlines()
        if line.strip()
    ]

    assert response.status_code == 200
    assert events[0] == {"type": "delta", "content": "Hello"}
    assert events[1]["type"] == "error"
    assert "local AI model" in events[1]["error"]
    assert fake_memory.archived == []
    assert fake_memory.appended == []
    assert Message.query.count() == 0
