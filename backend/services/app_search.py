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
_LEXICAL_WEIGHT = 0.3
_PRIORITY_TOKEN_WEIGHT = 0.3


@dataclass(frozen=True)
class AppMatch:
    app: AppManifestEntry
    score: float


@dataclass(frozen=True)
class AppSearchIndex:
    entries: tuple[AppManifestEntry, ...]
    embeddings: np.ndarray
    semantic_profiles: tuple[str, ...]
    profile_tokens: tuple[frozenset[str], ...]
    priority_tokens: tuple[frozenset[str], ...]
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
        """Return the best hybrid semantic/lexical match for a user query."""
        cleaned_query = normalize_query_text(query)
        if not cleaned_query or self.is_empty:
            return None

        query_tokens = query_token_set(cleaned_query)
        query_embedding = encode_sentences(model, cleaned_query)
        semantic_scores = self.embeddings @ query_embedding

        best_index = 0
        best_semantic_score = float("-inf")
        best_lexical_score = 0.0
        best_score = float("-inf")
        for index, semantic_score in enumerate(semantic_scores):
            lexical_score = compute_lexical_overlap_score(
                query_tokens,
                self.profile_tokens[index],
                self.priority_tokens[index],
            )
            final_score = combine_app_scores(
                float(semantic_score),
                lexical_score,
            )
            if final_score > best_score:
                best_index = index
                best_semantic_score = float(semantic_score)
                best_lexical_score = lexical_score
                best_score = final_score

        logger.info(
            (
                "App search query raw=%r normalized=%r query_tokens=%s best_app=%s "
                "semantic_score=%.3f lexical_score=%.3f final_score=%.3f matched_profile=%r"
            ),
            query,
            cleaned_query,
            sorted(query_tokens),
            self.entries[best_index].app_id,
            best_semantic_score,
            best_lexical_score,
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
            profile_tokens=tuple(),
            priority_tokens=tuple(),
            model_name=model_name,
        )

    if model is None:
        raise RuntimeError("Embedding model is required to build a non-empty app index")
    semantic_profiles = [build_semantic_profile(entry) for entry in entries]
    profile_tokens = [build_profile_token_set(entry) for entry in entries]
    priority_tokens = [build_priority_token_set(entry) for entry in entries]
    embeddings = encode_sentences(model, semantic_profiles)

    return AppSearchIndex(
        entries=tuple(entries),
        embeddings=embeddings,
        semantic_profiles=tuple(semantic_profiles),
        profile_tokens=tuple(profile_tokens),
        priority_tokens=tuple(priority_tokens),
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


def query_token_set(text: str) -> frozenset[str]:
    """Normalize a query into a unique set of content-bearing tokens."""
    normalized = normalize_query_text(text)
    if not normalized:
        return frozenset()
    return frozenset(normalized.split())


def build_profile_token_set(entry: AppManifestEntry) -> frozenset[str]:
    """Build a normalized token set for lexical overlap matching."""
    parts = [
        entry.name,
        entry.description,
        *entry.aliases,
        *entry.tags,
    ]
    return _content_token_set(" ".join(part for part in parts if part))


def build_priority_token_set(entry: AppManifestEntry) -> frozenset[str]:
    """Build higher-priority lexical tokens from aliases and tags."""
    parts = [
        *entry.aliases,
        *entry.tags,
    ]
    return _content_token_set(" ".join(part for part in parts if part))


def compute_lexical_overlap_score(
    query_tokens: frozenset[str],
    profile_tokens: frozenset[str],
    priority_tokens: frozenset[str],
) -> float:
    """Score lexical overlap cheaply using normalized token sets."""
    if not query_tokens or not profile_tokens:
        return 0.0

    overlap_ratio = len(query_tokens & profile_tokens) / len(query_tokens)
    priority_ratio = 0.0
    if priority_tokens:
        priority_ratio = len(query_tokens & priority_tokens) / len(query_tokens)
    lexical_score = ((1.0 - _PRIORITY_TOKEN_WEIGHT) * overlap_ratio) + (
        _PRIORITY_TOKEN_WEIGHT * priority_ratio
    )
    return min(1.0, lexical_score)


def combine_app_scores(semantic_score: float, lexical_score: float) -> float:
    """Blend semantic similarity with a lightweight lexical boost."""
    semantic_score = max(-1.0, min(1.0, semantic_score))
    lexical_score = max(0.0, min(1.0, lexical_score))
    return semantic_score + ((1.0 - semantic_score) * (_LEXICAL_WEIGHT * lexical_score))


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


def _content_token_set(text: str) -> frozenset[str]:
    """Keep only normalized non-stopword tokens for lexical matching."""
    return frozenset(token for token in _normalize_tokens(text) if token not in _STOPWORDS)
