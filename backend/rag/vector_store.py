from __future__ import annotations

import os
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import List, TYPE_CHECKING

logger = logging.getLogger(__name__)

try:
    import chromadb
except ModuleNotFoundError:
    chromadb = None
    logger.warning("RAG disabled (chromadb not installed)")

if TYPE_CHECKING:
    from .chunker import Chunk


DEFAULT_COLLECTION = os.getenv("CHROMA_COLLECTION", "app_knowledge")
DEFAULT_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "backend/data/chroma")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class VectorStoreConfig:
    persist_dir: str = DEFAULT_PERSIST_DIR
    collection_name: str = DEFAULT_COLLECTION


class VectorStore:
    def __init__(self, config: VectorStoreConfig | None = None) -> None:
        self.config = config or VectorStoreConfig()
        persist_dir = Path(self.config.persist_dir)
        if not persist_dir.is_absolute():
            persist_dir = PROJECT_ROOT / persist_dir
        self._persist_dir = persist_dir
        self.available = chromadb is not None
        if not self.available:
            self.client = None
            self.collection = None
            return
        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(self.config.collection_name)

    def reset(self) -> None:
        if not self.available:
            return
        self.client.delete_collection(self.config.collection_name)
        self.collection = self.client.get_or_create_collection(self.config.collection_name)

    def add_documents(
        self,
        *,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
    ) -> None:
        if not self.available:
            return
        self.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def add_chunks(self, *, chunks: List["Chunk"], embeddings: List[List[float]]) -> None:
        if not self.available:
            return
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        self.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def upsert(self, *, ids: List[str], documents: List[str], embeddings: List[List[float]], metadatas: List[dict]) -> None:
        if not self.available:
            return
        self.collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query(self, *, query_embeddings: List[List[float]], n_results: int) -> dict | list:
        if not self.available:
            return []
        return self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            include=["documents", "metadatas", "distances", "ids"],
        )

    def retrieve(self, *, query_embeddings: List[List[float]], n_results: int) -> dict | list:
        return self.query(query_embeddings=query_embeddings, n_results=n_results)

    def count(self) -> int:
        if not self.available:
            return 0
        return self.collection.count()
