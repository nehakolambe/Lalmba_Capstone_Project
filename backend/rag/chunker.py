from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .loader import Document


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: dict


def chunk_text(text: str, *, max_chars: int = 800, overlap: int = 150) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + max_chars, length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def chunk_documents(documents: Iterable[Document]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for doc in documents:
        for index, chunk in enumerate(chunk_text(doc.text)):
            chunk_id = f"{doc.doc_id}::chunk-{index}"
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = index
            chunks.append(Chunk(chunk_id=chunk_id, text=chunk, metadata=metadata))
    return chunks
