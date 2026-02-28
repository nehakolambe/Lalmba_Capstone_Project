from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend import create_app
from backend.config import TestConfig
from backend.services.app_manifest import AppManifestError, load_app_manifest
from backend.services.app_search import build_app_index


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "data" / "app_manifest.json"


class FakeEmbeddingModel:
    def __init__(self, mapping):
        self.mapping = mapping

    def encode(
        self,
        sentences,
        *,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ):
        if isinstance(sentences, str):
            return self.mapping[sentences]
        return [self.mapping[sentence] for sentence in sentences]


def test_load_app_manifest_success(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            [
                {
                    "app_id": "tux_typing",
                    "name": "Tux Typing",
                    "description": "Typing game",
                    "tutorial_steps": ["Open it"],
                }
            ]
        ),
        encoding="utf-8",
    )

    entries = load_app_manifest(path)

    assert len(entries) == 1
    assert entries[0].app_id == "tux_typing"
    assert entries[0].tutorial_steps == ("Open it",)


def test_load_app_manifest_rejects_invalid_entry(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            [
                {
                    "app_id": "tux_typing",
                    "name": "",
                    "description": "Typing game",
                    "tutorial_steps": ["Open it"],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(AppManifestError, match="field 'name'"):
        load_app_manifest(path)


def test_build_app_index_returns_best_match():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    model = FakeEmbeddingModel(
        {
            manifest_entries[0].description: [1.0, 0.0, 0.0],
            manifest_entries[1].description: [0.0, 1.0, 0.0],
            manifest_entries[2].description: [0.0, 0.0, 1.0],
            "I want a drawing app": [0.0, 1.0, 0.0],
            "Something unrelated": [0.1, 0.1, 0.1],
        }
    )

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search("I want a drawing app", model, threshold=0.35)

    assert match is not None
    assert match.app.app_id == "tux_paint"
    assert match.score == pytest.approx(1.0)


def test_build_app_index_returns_none_below_threshold():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    model = FakeEmbeddingModel(
        {
            manifest_entries[0].description: [1.0, 0.0],
            manifest_entries[1].description: [0.0, 1.0],
            manifest_entries[2].description: [-1.0, 0.0],
            "Something unrelated": [0.1, -0.1],
        }
    )

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search("Something unrelated", model, threshold=0.8)

    assert match is None


def test_build_app_index_handles_empty_manifest():
    model = FakeEmbeddingModel({})

    index = build_app_index([], model, model_name="fake-model")

    assert index.is_empty is True
    assert index.search("drawing", model, threshold=0.1) is None


def test_startup_initializes_app_search(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "app_id": "tux_paint",
                    "name": "Tux Paint",
                    "description": "A drawing app",
                    "tutorial_steps": ["Open Tux Paint"],
                }
            ]
        ),
        encoding="utf-8",
    )

    fake_model = FakeEmbeddingModel(
        {
            "A drawing app": [0.0, 1.0],
            "drawing": [0.0, 1.0],
        }
    )

    monkeypatch.setattr(
        "backend.services.app_search.load_embedding_model",
        lambda _model_name: fake_model,
    )

    class SearchConfig(TestConfig):
        APP_SEARCH_ENABLED = True
        APP_MANIFEST_PATH = str(manifest_path)

    app = create_app(SearchConfig)

    with app.app_context():
        index = app.extensions["app_search_index"]
        assert len(index.entries) == 1
        match = index.search("drawing", app.extensions["app_search_model"], threshold=0.3)
        assert match is not None
        assert match.app.name == "Tux Paint"


def test_startup_allows_empty_manifest(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(
        "backend.services.app_search.load_embedding_model",
        lambda _model_name: FakeEmbeddingModel({}),
    )

    class SearchConfig(TestConfig):
        APP_SEARCH_ENABLED = True
        APP_MANIFEST_PATH = str(manifest_path)

    app = create_app(SearchConfig)

    with app.app_context():
        index = app.extensions["app_search_index"]
        assert index.is_empty is True


def test_startup_fails_for_invalid_manifest(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "app_id": "broken",
                    "name": "",
                    "description": "A broken app",
                    "tutorial_steps": ["Open it"],
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "backend.services.app_search.load_embedding_model",
        lambda _model_name: FakeEmbeddingModel({}),
    )

    class SearchConfig(TestConfig):
        APP_SEARCH_ENABLED = True
        APP_MANIFEST_PATH = str(manifest_path)

    with pytest.raises(AppManifestError):
        create_app(SearchConfig)
