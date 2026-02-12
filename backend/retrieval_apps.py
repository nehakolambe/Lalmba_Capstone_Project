from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import List, Optional

import requests
from sqlalchemy import select

from .extensions import db
from .models import AppDoc, AppEmbedding
from .services.ollama_client import OllamaError


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")
OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embed"
OLLAMA_EMBED_FALLBACK_URL = f"{OLLAMA_BASE_URL}/api/embeddings"


@dataclass(frozen=True)
class RetrievedApp:
    app_doc: AppDoc
    score: float


def _extract_embedding(data: object) -> Optional[List[float]]:
    if not isinstance(data, dict):
        return None
    embedding = data.get("embedding")
    if isinstance(embedding, list):
        return embedding
    embeddings = data.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, list):
            return first
    return None


def embed_query(text: str, *, model: str = OLLAMA_EMBED_MODEL) -> List[float]:
    if not text.strip():
        return []

    payload = {"model": model, "input": text}
    try:
        response = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise OllamaError(
            "Could not reach the local Ollama embedding model",
            reason=str(exc),
        ) from exc

    if response.status_code == 404:
        try:
            response = requests.post(
                OLLAMA_EMBED_FALLBACK_URL,
                json={"model": model, "prompt": text},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise OllamaError(
                "Could not reach the local Ollama embedding model",
                reason=str(exc),
            ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaError("Unexpected response from Ollama embeddings", reason="invalid_json") from exc

    if not response.ok:
        reason = data.get("error") if isinstance(data, dict) else response.text
        raise OllamaError("Ollama embedding error", reason=reason, status=response.status_code)

    embedding = _extract_embedding(data)
    if not embedding:
        raise OllamaError("Ollama embedding returned empty result", reason="empty_embedding")

    return embedding


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for idx, val in enumerate(vec_a):
        dot += val * vec_b[idx]
        norm_a += val * val
        norm_b += vec_b[idx] * vec_b[idx]
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def has_app_embeddings(*, model: str = OLLAMA_EMBED_MODEL) -> bool:
    return (
        db.session.query(AppEmbedding.id)
        .filter(AppEmbedding.embedding_model == model)
        .limit(1)
        .first()
        is not None
    )


def retrieve_top_k_apps(query: str, *, k: int = 5, model: str = OLLAMA_EMBED_MODEL, min_score: float = 0.0) -> List[RetrievedApp]:
    if not query.strip():
        return []

    query_embedding = embed_query(query, model=model)
    if not query_embedding:
        return []

    rows = db.session.execute(
        select(AppEmbedding, AppDoc)
        .join(AppDoc, AppEmbedding.app_doc_id == AppDoc.id)
        .where(AppEmbedding.embedding_model == model)
    ).all()

    results: List[RetrievedApp] = []
    for embedding_row, app_doc in rows:
        try:
            embedding = json.loads(embedding_row.embedding_json or "[]")
        except json.JSONDecodeError:
            embedding = []
        score = cosine_similarity(query_embedding, embedding)
        if score < min_score:
            continue
        results.append(RetrievedApp(app_doc=app_doc, score=score))

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:k]
