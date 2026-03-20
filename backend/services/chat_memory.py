from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from flask import Flask

from .conversation_state import CompletedTurn
from .embeddings import EmbeddingModel, encode_sentences, load_embedding_model

logger = logging.getLogger(__name__)

try:
    import chromadb
except ImportError:  # pragma: no cover
    chromadb = None


class ChromaCollection(Protocol):
    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        ...

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

    def get(
        self,
        *,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        ...

    def delete(
        self,
        *,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> None:
        ...


@dataclass(frozen=True)
class RetrievedMemory:
    document: str
    score: float
    timestamp: str | None
    turn_index: int | None


@dataclass(frozen=True)
class MemoryRetrievalResult:
    recent_turns: list[CompletedTurn]
    matches_returned: int
    matches_after_threshold: int
    matches_after_budget: int
    background_chars: int
    anchors: list[RetrievedMemory]


class ChatMemoryBuffer:
    """Lightweight per-thread FIFO memory kept only in-process."""

    def __init__(self, max_turns: int):
        self.max_turns = max(1, max_turns)
        self._buffers: dict[tuple[int, int], deque[CompletedTurn]] = defaultdict(
            lambda: deque(maxlen=self.max_turns)
        )

    def read(self, user_id: int, thread_id: int) -> list[CompletedTurn]:
        return list(self._buffers.get((user_id, thread_id), ()))

    def append(self, user_id: int, thread_id: int, turn: CompletedTurn) -> None:
        self._buffers[(user_id, thread_id)].append(turn)

    def clear_thread(self, user_id: int, thread_id: int) -> None:
        self._buffers.pop((user_id, thread_id), None)

    def clear_user(self, user_id: int) -> None:
        stale_keys = [key for key in self._buffers if key[0] == user_id]
        for key in stale_keys:
            self._buffers.pop(key, None)


class ChatMemoryService:
    """Retrieve and persist long-term and short-term conversation memory."""

    def __init__(
        self,
        *,
        model: EmbeddingModel,
        collection: ChromaCollection,
        buffer: ChatMemoryBuffer,
        top_k: int,
        threshold: float,
        anchor_char_budget: int,
    ):
        self.model = model
        self.collection = collection
        self.buffer = buffer
        self.top_k = max(1, top_k)
        self.threshold = threshold
        self.anchor_char_budget = max(0, anchor_char_budget)

    def read_recent_turns(self, user_id: int, thread_id: int) -> list[CompletedTurn]:
        return self.buffer.read(user_id, thread_id)

    def retrieve_context(
        self,
        user_id: int,
        thread_id: int,
        query_text: str,
    ) -> MemoryRetrievalResult:
        recent_turns = self.buffer.read(user_id, thread_id)
        cleaned_query = (query_text or "").strip()
        if not cleaned_query:
            return MemoryRetrievalResult(recent_turns, 0, 0, 0, 0, [])

        query_embedding = encode_sentences(self.model, cleaned_query)
        result = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=self.top_k,
            where=self._thread_filter(user_id, thread_id),
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        matches_returned = len(documents)

        thresholded: list[RetrievedMemory] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            score = 1.0 - float(distance)
            if score < self.threshold:
                continue
            metadata = metadata or {}
            thresholded.append(
                RetrievedMemory(
                    document=document,
                    score=score,
                    timestamp=metadata.get("timestamp"),
                    turn_index=metadata.get("turn_index"),
                )
            )

        kept: list[RetrievedMemory] = []
        used_chars = 0
        for anchor in thresholded:
            anchor_chars = len(anchor.document)
            if kept and used_chars + anchor_chars > self.anchor_char_budget:
                break
            if not kept and anchor_chars > self.anchor_char_budget > 0:
                break
            if self.anchor_char_budget == 0:
                break
            kept.append(anchor)
            used_chars += anchor_chars

        return MemoryRetrievalResult(
            recent_turns=recent_turns,
            matches_returned=matches_returned,
            matches_after_threshold=len(thresholded),
            matches_after_budget=len(kept),
            background_chars=used_chars,
            anchors=kept,
        )

    def archive_turn(
        self,
        *,
        user_id: int,
        thread_id: int,
        query_text: str,
        response_text: str,
        timestamp: datetime | None = None,
    ) -> str:
        turn_index = self.next_turn_index(user_id, thread_id)
        doc_id = self._doc_id(user_id, thread_id, turn_index)
        created_at = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc)
        document = self._format_document(query_text, response_text)
        embedding = encode_sentences(self.model, document).tolist()
        self.collection.add(
            ids=[doc_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[
                {
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "timestamp": created_at.isoformat(),
                    "turn_index": turn_index,
                }
            ],
        )
        return doc_id

    def append_recent_turn(
        self,
        user_id: int,
        thread_id: int,
        query_text: str,
        response_text: str,
    ) -> None:
        self.buffer.append(
            user_id,
            thread_id,
            CompletedTurn(user_text=query_text, assistant_text=response_text),
        )

    def clear_user(self, user_id: int) -> None:
        self.buffer.clear_user(user_id)
        self.collection.delete(where={"user_id": str(user_id)})

    def clear_thread(self, user_id: int, thread_id: int) -> None:
        self.buffer.clear_thread(user_id, thread_id)
        self.collection.delete(where=self._thread_filter(user_id, thread_id))

    def delete_archive_doc(self, doc_id: str) -> None:
        self.collection.delete(ids=[doc_id])

    def next_turn_index(self, user_id: int, thread_id: int) -> int:
        result = self.collection.get(
            where=self._thread_filter(user_id, thread_id),
            include=[],
        )
        return len(result.get("ids") or []) + 1

    @staticmethod
    def _format_document(query_text: str, response_text: str) -> str:
        return f"User: {query_text}\nAssistant: {response_text}"

    @staticmethod
    def _doc_id(user_id: int, thread_id: int, turn_index: int) -> str:
        return f"user-{user_id}-thread-{thread_id}-turn-{turn_index}"

    @staticmethod
    def _thread_filter(user_id: int, thread_id: int) -> dict[str, list[dict[str, str]]]:
        return {
            "$and": [
                {"user_id": {"$eq": str(user_id)}},
                {"thread_id": {"$eq": str(thread_id)}},
            ]
        }


def initialize_chat_memory(app: Flask) -> ChatMemoryService | None:
    """Initialize persistent chat memory for retrieval-based conversation context."""
    if not app.config.get("CHAT_MEMORY_ENABLED", True):
        app.extensions["chat_memory"] = None
        return None

    collection = _create_chroma_collection(
        app.config["CHAT_MEMORY_PERSIST_DIR"],
        app.config["CHAT_MEMORY_COLLECTION_NAME"],
    )
    model_name = app.config["CHAT_MEMORY_EMBEDDING_MODEL"] or app.config["APP_EMBEDDING_MODEL"]
    service = ChatMemoryService(
        model=load_embedding_model(model_name),
        collection=collection,
        buffer=ChatMemoryBuffer(app.config["CHAT_MEMORY_FIFO_TURNS"]),
        top_k=app.config["CHAT_MEMORY_TOP_K"],
        threshold=app.config["CHAT_MEMORY_SCORE_THRESHOLD"],
        anchor_char_budget=app.config["CHAT_MEMORY_ANCHOR_CHAR_BUDGET"],
    )
    app.extensions["chat_memory"] = service
    logger.info(
        "Chat memory initialized collection=%s model=%s persist_dir=%s",
        app.config["CHAT_MEMORY_COLLECTION_NAME"],
        model_name,
        Path(app.config["CHAT_MEMORY_PERSIST_DIR"]),
    )
    return service


def get_chat_memory(app: Flask) -> ChatMemoryService | None:
    return app.extensions.get("chat_memory")


def _create_chroma_collection(persist_dir: str, collection_name: str) -> ChromaCollection:
    if chromadb is None:
        raise RuntimeError(
            "chromadb is required for chat memory. "
            "Install backend dependencies before starting the server."
        )

    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path))
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
