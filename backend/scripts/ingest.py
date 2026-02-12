from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.rag.chunker import chunk_documents
from backend.rag.embeddings import embed_texts
from backend.rag.loader import load_markdown_documents
from backend.rag.vector_store import VectorStore, VectorStoreConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest app documentation into Chroma.")
    parser.add_argument("--source", default="knowledge_base/apps", help="Folder with markdown docs")
    parser.add_argument("--persist", default="backend/data/chroma", help="Chroma persistence directory")
    parser.add_argument("--collection", default="app_knowledge", help="Chroma collection name")
    parser.add_argument("--reset", action="store_true", help="Clear existing collection before ingest")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    source_dir = Path(args.source)
    if not source_dir.is_absolute():
        source_dir = PROJECT_ROOT / source_dir
    persist_dir = Path(args.persist)
    if not persist_dir.is_absolute():
        persist_dir = PROJECT_ROOT / persist_dir

    documents = load_markdown_documents(source_dir)
    chunks = chunk_documents(documents)

    if not chunks:
        print("No documents found to ingest.")
        return

    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts)
    metadatas = [chunk.metadata for chunk in chunks]
    ids = [chunk.chunk_id for chunk in chunks]

    store = VectorStore(
        VectorStoreConfig(persist_dir=str(persist_dir), collection_name=args.collection)
    )
    if args.reset:
        store.reset()

    store.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    status = {
        "last_ingest_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": source_dir.resolve().as_posix(),
        "collection": args.collection,
        "count": store.count(),
    }

    status_path = persist_dir / "ingest_status.json"
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    print(f"Ingested {len(chunks)} chunks into '{args.collection}'.")


if __name__ == "__main__":
    main()
