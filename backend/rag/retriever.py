from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .embeddings import embed_text
from .vector_store import VectorStore, VectorStoreConfig


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    content: str
    metadata: dict
    distance: float

    @property
    def snippet(self) -> str:
        return (self.content or "").strip()[:320]


def retrieve_chunks(query: str, *, k: int = 5, config: VectorStoreConfig | None = None) -> List[RetrievedChunk]:
    if not query.strip():
        return []

    store = VectorStore(config)
    if not store.available:
        return []
    if store.count() == 0:
        return []

    embedding = embed_text(query)
    raw = store.query(query_embeddings=[embedding], n_results=k)
    if not raw:
        return []

    chunks: List[RetrievedChunk] = []
    for idx, chunk_id in enumerate(raw.get("ids", [[]])[0]):
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                content=documents[idx] if idx < len(documents) else "",
                metadata=metadatas[idx] if idx < len(metadatas) else {},
                distance=distances[idx] if idx < len(distances) else 0.0,
            )
        )
    return chunks
