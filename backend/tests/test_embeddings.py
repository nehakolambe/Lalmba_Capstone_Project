from __future__ import annotations

from backend.services import embeddings


def test_load_embedding_model_uses_cpu(monkeypatch):
    captured = {}

    class FakeSentenceTransformer:
        def __init__(self, model_name, device=None):
            captured["model_name"] = model_name
            captured["device"] = device

    monkeypatch.setattr(embeddings, "SentenceTransformer", FakeSentenceTransformer)

    embeddings.load_embedding_model("all-MiniLM-L6-v2")

    assert captured["model_name"] == "all-MiniLM-L6-v2"
    assert captured["device"] == "cpu"
