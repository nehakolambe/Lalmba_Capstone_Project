from __future__ import annotations

from backend import create_app
from backend.config import TestConfig
from backend.services.chat_memory import (
    ChatMemoryBuffer,
    ChatMemoryService,
    _versioned_collection_name,
)
from backend.services.conversation_state import CompletedTurn


class FakeEmbeddingModel:
    def __init__(self, mapping):
        self.mapping = mapping

    def encode(
        self,
        sentences,
        *,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ):
        if isinstance(sentences, str):
            return self.mapping[sentences]
        return [self.mapping[sentence] for sentence in sentences]


class FakeCollection:
    def __init__(self):
        self.items = []

    @staticmethod
    def _matches_where(metadata, where):
        if where is None:
            return True
        if "$and" in where:
            return all(FakeCollection._matches_where(metadata, clause) for clause in where["$and"])
        for key, value in where.items():
            if isinstance(value, dict) and "$eq" in value:
                if metadata.get(key) != value["$eq"]:
                    return False
                continue
            if metadata.get(key) != value:
                return False
        return True

    def add(self, *, ids, documents, embeddings, metadatas):
        for item in zip(ids, documents, embeddings, metadatas):
            self.items.append(item)

    def query(self, *, query_embeddings, n_results, where=None, include=None):
        filtered = [
            item
            for item in self.items
            if self._matches_where(item[3], where)
        ]
        distances = []
        for _item in filtered[:n_results]:
            metadata = _item[3]
            distances.append(metadata.get("distance", 0.0))
        return {
            "documents": [[item[1] for item in filtered[:n_results]]],
            "metadatas": [[item[3] for item in filtered[:n_results]]],
            "distances": [distances],
        }

    def get(self, *, where=None, include=None):
        filtered = [
            item
            for item in self.items
            if self._matches_where(item[3], where)
        ]
        return {"ids": [item[0] for item in filtered]}

    def delete(self, *, ids=None, where=None):
        if ids is not None:
            self.items = [item for item in self.items if item[0] not in set(ids)]
            return
        self.items = [
            item
            for item in self.items
            if not self._matches_where(item[3], where)
        ]


def test_chat_memory_buffer_eviction():
    buffer = ChatMemoryBuffer(max_turns=3)

    for index in range(4):
        buffer.append(
            1,
            10,
            CompletedTurn(user_text=f"user {index}", assistant_text=f"assistant {index}"),
        )

    recent = buffer.read(1, 10)
    assert len(recent) == 3
    assert recent[0].user_text == "user 1"
    assert recent[-1].assistant_text == "assistant 3"


def test_chat_memory_archive_format_and_metadata():
    collection = FakeCollection()
    service = ChatMemoryService(
        model=FakeEmbeddingModel({"User: Hi\nAssistant: Hello": [1.0, 0.0]}),
        collection=collection,
        buffer=ChatMemoryBuffer(max_turns=3),
        top_k=5,
        threshold=0.35,
        anchor_char_budget=1200,
    )

    doc_id = service.archive_turn(user_id=2, thread_id=7, query_text="Hi", response_text="Hello")

    assert doc_id == "user-2-thread-7-turn-1"
    stored = collection.items[0]
    assert stored[1] == "User: Hi\nAssistant: Hello"
    assert stored[3]["user_id"] == "2"
    assert stored[3]["thread_id"] == "7"
    assert stored[3]["turn_index"] == 1
    assert "timestamp" in stored[3]


def test_chat_memory_threshold_and_budget_filtering():
    collection = FakeCollection()
    collection.items = [
        (
            "user-1-thread-10-turn-1",
            "User: First\nAssistant: Response one",
            [1.0, 0.0],
            {"user_id": "1", "thread_id": "10", "turn_index": 1, "distance": 0.1},
        ),
        (
            "user-1-thread-10-turn-2",
            "User: Second\nAssistant: Response two that is too long",
            [1.0, 0.0],
            {"user_id": "1", "thread_id": "10", "turn_index": 2, "distance": 0.2},
        ),
        (
            "user-2-thread-20-turn-1",
            "User: Other\nAssistant: Other user",
            [1.0, 0.0],
            {"user_id": "2", "thread_id": "20", "turn_index": 1, "distance": 0.0},
        ),
    ]
    service = ChatMemoryService(
        model=FakeEmbeddingModel({"current query": [1.0, 0.0]}),
        collection=collection,
        buffer=ChatMemoryBuffer(max_turns=3),
        top_k=5,
        threshold=0.75,
        anchor_char_budget=40,
    )

    result = service.retrieve_context(1, 10, "current query")

    assert result.matches_returned == 2
    assert result.matches_after_threshold == 2
    assert result.matches_after_budget == 1
    assert result.anchors[0].document == "User: First\nAssistant: Response one"


def test_chat_memory_clear_thread_removes_only_selected_thread_memory():
    collection = FakeCollection()
    service = ChatMemoryService(
        model=FakeEmbeddingModel({"User: Hi\nAssistant: Hello": [1.0, 0.0]}),
        collection=collection,
        buffer=ChatMemoryBuffer(max_turns=3),
        top_k=5,
        threshold=0.35,
        anchor_char_budget=1200,
    )
    service.append_recent_turn(4, 2, "Hi", "Hello")
    service.append_recent_turn(4, 3, "Other", "Thread")
    service.archive_turn(user_id=4, thread_id=2, query_text="Hi", response_text="Hello")
    service.archive_turn(user_id=4, thread_id=3, query_text="Other", response_text="Thread")

    service.clear_thread(4, 2)

    assert service.read_recent_turns(4, 2) == []
    assert service.read_recent_turns(4, 3) != []
    assert collection.get(where={"user_id": "4", "thread_id": "2"}, include=[])["ids"] == []
    assert collection.get(where={"user_id": "4", "thread_id": "3"}, include=[])["ids"] != []


def test_versioned_collection_name_changes_when_model_changes():
    english_collection = _versioned_collection_name("chat_memory", "all-MiniLM-L6-v2")
    multilingual_collection = _versioned_collection_name(
        "chat_memory",
        "paraphrase-multilingual-MiniLM-L12-v2",
    )

    assert english_collection != multilingual_collection
    assert english_collection.startswith("chat_memory-")
    assert multilingual_collection.startswith("chat_memory-")


def test_startup_uses_model_specific_chat_memory_collection_name(monkeypatch, tmp_path):
    captured = {}
    fake_collection = FakeCollection()

    monkeypatch.setattr(
        "backend.services.chat_memory.load_embedding_model",
        lambda _model_name: FakeEmbeddingModel({}),
    )

    def fake_create_chroma_collection(persist_dir, collection_name):
        captured["persist_dir"] = persist_dir
        captured["collection_name"] = collection_name
        return fake_collection

    monkeypatch.setattr(
        "backend.services.chat_memory._create_chroma_collection",
        fake_create_chroma_collection,
    )

    class ChatMemoryConfig(TestConfig):
        CHAT_MEMORY_ENABLED = True
        CHAT_MEMORY_PERSIST_DIR = str(tmp_path / "chat-memory")
        CHAT_MEMORY_COLLECTION_NAME = "chat_memory"
        APP_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    app = create_app(ChatMemoryConfig)

    with app.app_context():
        assert captured["persist_dir"] == str(tmp_path / "chat-memory")
        assert captured["collection_name"] == _versioned_collection_name(
            "chat_memory",
            "paraphrase-multilingual-MiniLM-L12-v2",
        )
        assert app.extensions["chat_memory"].collection is fake_collection
