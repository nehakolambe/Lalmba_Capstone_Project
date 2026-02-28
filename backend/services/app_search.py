from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from flask import Flask

from .app_manifest import AppManifestEntry, load_app_manifest

logger = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class AppMatch:
    app: AppManifestEntry
    score: float


@dataclass(frozen=True)
class AppSearchIndex:
    entries: tuple[AppManifestEntry, ...]
    embeddings: np.ndarray
    model_name: str

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def search(
        self,
        query: str,
        model: EmbeddingModel,
        *,
        threshold: float,
    ) -> AppMatch | None:
        """Return the best semantic match for a user query."""
        cleaned_query = (query or "").strip()
        if not cleaned_query or self.is_empty:
            return None

        query_embedding = _encode_sentences(model, cleaned_query)
        scores = self.embeddings @ query_embedding
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        if best_score < threshold:
            return None
        return AppMatch(app=self.entries[best_index], score=best_score)


def initialize_app_search(app: Flask) -> AppSearchIndex:
    """Load the local app manifest and build the embedding index."""
    manifest_path = app.config["APP_MANIFEST_PATH"]
    model_name = app.config["APP_EMBEDDING_MODEL"]
    entries = load_app_manifest(manifest_path)
    model = None
    if entries:
        model = load_embedding_model(model_name)
    index = build_app_index(entries, model, model_name=model_name)
    app.extensions["app_search_model"] = model
    app.extensions["app_search_index"] = index
    logger.info(
        "App search initialized with %s apps from %s using model %s",
        len(index.entries),
        Path(manifest_path),
        model_name,
    )
    return index


def get_app_search_index(app: Flask) -> AppSearchIndex | None:
    """Return the initialized app search index for the current Flask app."""
    return app.extensions.get("app_search_index")


def search_apps(
    app: Flask,
    query: str,
    *,
    threshold: float | None = None,
) -> AppMatch | None:
    """Search the initialized index using the configured model and threshold."""
    index = get_app_search_index(app)
    model = app.extensions.get("app_search_model")
    if index is None:
        raise RuntimeError("App search has not been initialized")
    if index.is_empty:
        return None
    if model is None:
        raise RuntimeError("App search model is unavailable")

    return index.search(
        query,
        model,
        threshold=float(
            app.config["APP_MATCH_THRESHOLD"] if threshold is None else threshold
        ),
    )


def load_embedding_model(model_name: str) -> EmbeddingModel:
    """Load the configured sentence-transformer model."""
    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence-transformers is required for app search. "
            "Install backend dependencies before starting the server."
        )
    return SentenceTransformer(model_name)


def build_app_index(
    entries: list[AppManifestEntry],
    model: EmbeddingModel | None,
    *,
    model_name: str,
) -> AppSearchIndex:
    """Embed app descriptions and build an in-memory similarity index."""
    if not entries:
        return AppSearchIndex(
            entries=tuple(),
            embeddings=np.empty((0, 0), dtype=np.float32),
            model_name=model_name,
        )

    descriptions = [entry.description for entry in entries]
    if model is None:
        raise RuntimeError("Embedding model is required to build a non-empty app index")
    embeddings = _encode_sentences(model, descriptions)

    return AppSearchIndex(
        entries=tuple(entries),
        embeddings=embeddings,
        model_name=model_name,
    )


def _encode_sentences(
    model: EmbeddingModel,
    sentences: str | list[str],
) -> np.ndarray:
    encoded = model.encode(
        sentences,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(encoded, dtype=np.float32)
