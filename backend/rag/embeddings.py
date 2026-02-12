from __future__ import annotations

import os
from typing import List

import requests

from ..services.ollama_client import OllamaError


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embeddings"
DEFAULT_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def embed_text(text: str, *, model: str = DEFAULT_EMBED_MODEL) -> List[float]:
    payload = {"model": model, "prompt": text}
    try:
        response = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
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

    embedding = data.get("embedding") if isinstance(data, dict) else None
    if not embedding:
        raise OllamaError("Ollama embedding returned empty result", reason="empty_embedding")

    return embedding


def embed_texts(texts: List[str], *, model: str = DEFAULT_EMBED_MODEL) -> List[List[float]]:
    embeddings: List[List[float]] = []
    for text in texts:
        embeddings.append(embed_text(text, model=model))
    return embeddings
