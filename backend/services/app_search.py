from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from flask import Flask
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from .app_manifest import AppManifestEntry, load_app_manifest
from .embeddings import EmbeddingModel, encode_sentences, load_embedding_model

logger = logging.getLogger(__name__)
_STOPWORDS = frozenset(ENGLISH_STOP_WORDS)


@dataclass(frozen=True)
class AppMatch:
    app: AppManifestEntry
    score: float


@dataclass(frozen=True)
class AppSearchIndex:
    entries: tuple[AppManifestEntry, ...]
    embeddings: np.ndarray
    semantic_profiles: tuple[str, ...]
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
        cleaned_query = normalize_query_text(query)
        if not cleaned_query or self.is_empty:
            return None

        query_embedding = encode_sentences(model, cleaned_query)
        scores = self.embeddings @ query_embedding
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        logger.info(
            "App search query raw=%r normalized=%r best_app=%s score=%.3f matched_profile=%r",
            query,
            cleaned_query,
            self.entries[best_index].app_id,
            best_score,
            self.semantic_profiles[best_index],
        )
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
    """Embed semantic app profiles and build an in-memory similarity index."""
    if not entries:
        return AppSearchIndex(
            entries=tuple(),
            embeddings=np.empty((0, 0), dtype=np.float32),
            semantic_profiles=tuple(),
            model_name=model_name,
        )

    if model is None:
        raise RuntimeError("Embedding model is required to build a non-empty app index")
    semantic_profiles = [build_semantic_profile(entry) for entry in entries]
    embeddings = encode_sentences(model, semantic_profiles)

    return AppSearchIndex(
        entries=tuple(entries),
        embeddings=embeddings,
        semantic_profiles=tuple(semantic_profiles),
        model_name=model_name,
    )


def build_semantic_profile(entry: AppManifestEntry) -> str:
    """Build normalized semantic text used to embed an app."""
    parts = [
        entry.name,
        entry.description,
        *entry.aliases,
        *entry.tags,
    ]
    return normalize_profile_text(" ".join(part for part in parts if part))


def normalize_query_text(text: str) -> str:
    """Normalize a user query and remove stopwords before embedding."""
    return " ".join(
        token for token in _normalize_tokens(text) if token not in _STOPWORDS
    )


def normalize_profile_text(text: str) -> str:
    """Normalize semantic profile text without removing stopwords."""
    return " ".join(_normalize_tokens(text))


def _normalize_tokens(text: str) -> list[str]:
    """Normalize text to stable token forms for semantic matching."""
    ascii_text = unicodedata.normalize("NFKD", (text or "").lower()).encode(
        "ascii", "ignore"
    ).decode("ascii")
    collapsed = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    tokens = [token for token in collapsed.split() if token]
    return [_reduce_token(token) for token in tokens if _reduce_token(token)]


def _reduce_token(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("'s"):
        return token[:-2]
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return _trim_doubled_tail(token[:-3])
    if len(token) > 4 and token.endswith("ed"):
        return _trim_doubled_tail(token[:-2])
    if len(token) > 4 and token.endswith("es") and not token.endswith(("ses", "xes", "zes")):
        return token[:-1]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _trim_doubled_tail(token: str) -> str:
    if len(token) >= 2 and token[-1] == token[-2]:
        return token[:-1]
    return token
