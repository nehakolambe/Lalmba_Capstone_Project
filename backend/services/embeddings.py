from __future__ import annotations

from typing import Any, Protocol

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None


class EmbeddingModel(Protocol):
    def encode(
        self,
        sentences: str | list[str],
        *,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
    ) -> Any:
        ...


def load_embedding_model(model_name: str) -> EmbeddingModel:
    """Load a sentence-transformer model on CPU to preserve llama.cpp VRAM."""
    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence-transformers is required for embeddings. "
            "Install backend dependencies before starting the server."
        )
    return SentenceTransformer(model_name, device="cpu")


def encode_sentences(
    model: EmbeddingModel,
    sentences: str | list[str],
) -> np.ndarray:
    """Encode one or more sentences as normalized float32 vectors."""
    encoded = model.encode(
        sentences,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(encoded, dtype=np.float32)
