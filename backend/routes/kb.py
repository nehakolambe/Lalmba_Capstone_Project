from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from flask import jsonify, request

from ..rag.chunker import chunk_documents
from ..rag.embeddings import embed_texts
from ..rag.loader import load_markdown_documents
from ..rag.vector_store import VectorStore, VectorStoreConfig
from . import kb_bp

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _status_path(persist_dir: str) -> Path:
    return Path(persist_dir) / "ingest_status.json"


@kb_bp.post("/kb/ingest")
def ingest_kb():
    payload = request.get_json(silent=True) or {}
    source_dir = (payload.get("source_dir") or "knowledge_base/apps").strip()
    persist_dir = (payload.get("persist_dir") or "backend/data/chroma").strip()
    collection = (payload.get("collection") or "app_knowledge").strip()
    reset = bool(payload.get("reset"))

    source_path = Path(source_dir)
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path

    persist_path = Path(persist_dir)
    if not persist_path.is_absolute():
        persist_path = PROJECT_ROOT / persist_path

    documents = load_markdown_documents(source_path)
    chunks = chunk_documents(documents)
    if not chunks:
        return jsonify({"message": "No documents found to ingest.", "count": 0}), 400

    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts)
    metadatas = [chunk.metadata for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]

    store = VectorStore(
        VectorStoreConfig(persist_dir=str(persist_path), collection_name=collection)
    )
    if reset:
        store.reset()

    store.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    status = {
        "last_ingest_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": source_path.resolve().as_posix(),
        "collection": collection,
        "count": store.count(),
    }
    _status_path(str(persist_path)).write_text(json.dumps(status, indent=2), encoding="utf-8")

    return jsonify(status), 201


@kb_bp.get("/kb/status")
def kb_status():
    persist_dir = (request.args.get("persist_dir") or "backend/data/chroma").strip()
    persist_path = Path(persist_dir)
    if not persist_path.is_absolute():
        persist_path = PROJECT_ROOT / persist_path
    status_file = _status_path(str(persist_path))
    status = {}
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status = {}

    store = VectorStore(VectorStoreConfig(persist_dir=str(persist_path)))
    status.setdefault("count", store.count())
    status.setdefault("collection", store.config.collection_name)
    return jsonify(status)
