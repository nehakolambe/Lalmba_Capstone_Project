from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from flask import Flask

from .app_manifest import AppManifestEntry, load_app_manifest
from .embeddings import EmbeddingModel, encode_sentences, load_embedding_model

logger = logging.getLogger(__name__)


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

        query_embedding = encode_sentences(model, cleaned_query)
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


def get_app_by_id(app: Flask, app_id: str) -> AppManifestEntry | None:
    """Return a manifest entry by id from the initialized search index."""
    index = get_app_search_index(app)
    if index is None or not app_id:
        return None
    for entry in index.entries:
        if entry.app_id == app_id:
            return entry
    return None


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
    embeddings = encode_sentences(model, descriptions)

    return AppSearchIndex(entries=tuple(entries), embeddings=embeddings, model_name=model_name)
