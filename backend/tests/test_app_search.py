from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend import create_app
from backend.config import TestConfig
from backend.services.app_manifest import AppManifestError, load_app_manifest
from backend.services.app_search import (
    build_app_index,
    build_semantic_profile,
    compute_lexical_overlap_score,
    normalize_profile_text,
    normalize_query_text,
    query_token_set,
)


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


def _entry_by_app_id(entries, app_id):
    return next(entry for entry in entries if entry.app_id == app_id)


def _one_hot_manifest_mapping(entries, dimensions):
    mapping = {}
    for index, entry in enumerate(entries):
        vector = [0.0] * dimensions
        vector[index] = 1.0
        mapping[build_semantic_profile(entry)] = vector
    return mapping


def _vector(dimensions, *pairs):
    values = [0.0] * dimensions
    for index, value in pairs:
        values[index] = value
    return values


def test_load_app_manifest_success(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            [
                {
                    "app_id": "tux_typing",
                    "name": "Tux Typing",
                    "description": "Typing game",
                    "aliases": ["Typing tutor"],
                    "tags": ["typing", "keyboard"],
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
    assert entries[0].aliases == ("Typing tutor",)
    assert entries[0].tags == ("typing", "keyboard")


def test_load_app_manifest_rejects_invalid_entry(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            [
                {
                    "app_id": "tux_typing",
                    "name": "Tux Typing",
                    "description": "Typing game",
                    "aliases": [""],
                    "tutorial_steps": ["Open it"],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(AppManifestError, match="field 'aliases' item 0"):
        load_app_manifest(path)


def test_build_app_index_returns_best_match():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    dimensions = len(manifest_entries)
    tux_typing = _entry_by_app_id(manifest_entries, "tux_typing")
    tux_paint = _entry_by_app_id(manifest_entries, "tux_paint")
    model_mapping = _one_hot_manifest_mapping(manifest_entries, dimensions)
    model_mapping[normalize_query_text("I want a drawing app")] = model_mapping[
        build_semantic_profile(tux_paint)
    ]
    model_mapping[normalize_query_text("Something unrelated")] = [0.1] * dimensions
    model = FakeEmbeddingModel(model_mapping)

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search("I want a drawing app", model, threshold=0.35)

    assert match is not None
    assert match.app.app_id == "tux_paint"
    assert match.score == pytest.approx(1.0)


def test_build_app_index_returns_none_below_threshold():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    dimensions = len(manifest_entries)
    tux_typing = _entry_by_app_id(manifest_entries, "tux_typing")
    tux_paint = _entry_by_app_id(manifest_entries, "tux_paint")
    tux_math = _entry_by_app_id(manifest_entries, "tux_math")
    model_mapping = _one_hot_manifest_mapping(manifest_entries, dimensions)
    model_mapping[build_semantic_profile(tux_typing)] = _vector(dimensions, (0, 1.0))
    model_mapping[build_semantic_profile(tux_paint)] = _vector(dimensions, (1, 1.0))
    model_mapping[build_semantic_profile(tux_math)] = _vector(dimensions, (0, -1.0))
    model_mapping[normalize_query_text("Something unrelated")] = _vector(
        dimensions, (0, 0.1), (1, -0.1)
    )
    model = FakeEmbeddingModel(model_mapping)

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search("Something unrelated", model, threshold=0.8)

    assert match is None


def test_build_app_index_uses_lexical_boost_for_short_topic_question():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    dimensions = len(manifest_entries)
    biology = _entry_by_app_id(manifest_entries, "biology")
    tux_typing = _entry_by_app_id(manifest_entries, "tux_typing")
    model_mapping = _one_hot_manifest_mapping(manifest_entries, dimensions)
    model_mapping[build_semantic_profile(biology)] = _vector(dimensions, (4, 1.0))
    model_mapping[build_semantic_profile(tux_typing)] = _vector(dimensions, (0, 1.0))
    model_mapping[normalize_query_text("what does plants eat?")] = _vector(
        dimensions, (4, 0.29), (0, 0.24)
    )
    model = FakeEmbeddingModel(model_mapping)

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search("what does plants eat?", model, threshold=0.35)

    assert match is not None
    assert match.app.app_id == "biology"
    assert match.score >= 0.35


def test_build_app_index_supports_swahili_query_with_multilingual_embeddings():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    dimensions = len(manifest_entries)
    tux_typing = _entry_by_app_id(manifest_entries, "tux_typing")
    model_mapping = _one_hot_manifest_mapping(manifest_entries, dimensions)
    model_mapping[normalize_query_text("programu ya kujifunza kuchapa")] = model_mapping[
        build_semantic_profile(tux_typing)
    ]
    model = FakeEmbeddingModel(model_mapping)

    index = build_app_index(manifest_entries, model, model_name="fake-multilingual-model")
    match = index.search("programu ya kujifunza kuchapa", model, threshold=0.35)

    assert match is not None
    assert match.app.app_id == "tux_typing"


def test_build_app_index_still_returns_none_for_unrelated_query_with_no_overlap():
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    dimensions = len(manifest_entries)
    model_mapping = _one_hot_manifest_mapping(manifest_entries, dimensions)
    model_mapping[normalize_query_text("how to fix a spaceship engine")] = [0.12] * dimensions
    model = FakeEmbeddingModel(model_mapping)

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search("how to fix a spaceship engine", model, threshold=0.35)

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
                    "aliases": ["Paint program"],
                    "tags": ["drawing", "art"],
                    "tutorial_steps": ["Open Tux Paint"],
                }
            ]
        ),
        encoding="utf-8",
    )

    profile = normalize_profile_text("Tux Paint A drawing app Paint program drawing art")
    fake_model = FakeEmbeddingModel(
        {
            profile: [0.0, 1.0],
            normalize_query_text("drawing"): [0.0, 1.0],
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


@pytest.mark.parametrize(
    ("query", "expected_app_id"),
    [
        ("I want to learn maths", "tux_math"),
        ("I want to learn paint", "tux_paint"),
        ("my child wants to make pictures", "tux_paint"),
        ("I need keyboard practice", "tux_typing"),
        ("I want something fun for numbers", "tux_math"),
        ("show me a science experiment", "physics"),
        ("I want to learn about animals and plants", "biology"),
        ("teach me about growing crops", "farming"),
        ("I need help with geometry graphs", "geogebra"),
        ("I need a basic calculator for numbers", "calculator"),
        ("teach me business marketing skills", "google_primer"),
        ("I want to learn about nutrition and hygiene", "health"),
        ("show me a step by step guide", "how_to"),
        ("help me learn budgeting and investing", "investopedia"),
        ("teach me about clean water and waste", "sanitation"),
        ("my child wants to make a coding game", "scratch"),
    ],
)
def test_build_app_index_matches_direct_and_indirect_queries(query, expected_app_id):
    manifest_entries = load_app_manifest(MANIFEST_PATH)
    tux_typing = _entry_by_app_id(manifest_entries, "tux_typing")
    tux_paint = _entry_by_app_id(manifest_entries, "tux_paint")
    tux_math = _entry_by_app_id(manifest_entries, "tux_math")
    physics = _entry_by_app_id(manifest_entries, "physics")
    biology = _entry_by_app_id(manifest_entries, "biology")
    farming = _entry_by_app_id(manifest_entries, "farming")
    geogebra = _entry_by_app_id(manifest_entries, "geogebra")
    calculator = _entry_by_app_id(manifest_entries, "calculator")
    google_primer = _entry_by_app_id(manifest_entries, "google_primer")
    health = _entry_by_app_id(manifest_entries, "health")
    how_to = _entry_by_app_id(manifest_entries, "how_to")
    investopedia = _entry_by_app_id(manifest_entries, "investopedia")
    sanitation = _entry_by_app_id(manifest_entries, "sanitation")
    scratch = _entry_by_app_id(manifest_entries, "scratch")
    model = FakeEmbeddingModel(
        {
            build_semantic_profile(tux_typing): [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(tux_paint): [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(tux_math): [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(physics): [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(biology): [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(farming): [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(geogebra): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(calculator): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(google_primer): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(health): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            build_semantic_profile(how_to): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            build_semantic_profile(investopedia): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            build_semantic_profile(sanitation): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            build_semantic_profile(scratch): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            normalize_query_text("I want to learn maths"): [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I want to learn paint"): [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("my child wants to make pictures"): [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I need keyboard practice"): [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I want something fun for numbers"): [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("show me a science experiment"): [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I want to learn about animals and plants"): [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("teach me about growing crops"): [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I need help with geometry graphs"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I need a basic calculator for numbers"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("teach me business marketing skills"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("I want to learn about nutrition and hygiene"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            normalize_query_text("show me a step by step guide"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            normalize_query_text("help me learn budgeting and investing"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            normalize_query_text("teach me about clean water and waste"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            normalize_query_text("my child wants to make a coding game"): [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        }
    )

    index = build_app_index(manifest_entries, model, model_name="fake-model")
    match = index.search(query, model, threshold=0.35)

    assert match is not None
    assert match.app.app_id == expected_app_id


def test_normalize_query_text_keeps_multilingual_terms_without_english_stemming():
    assert normalize_query_text("  I want to learn MATHS!! ") == "i want to learn maths"
    assert normalize_query_text("Can you help me with keyboard practice") == "can you help me with keyboard practice"
    assert normalize_query_text("My child wants to make pictures") == "my child wants to make pictures"
    assert normalize_query_text("Ninataka kujifunza kuchapa") == "ninataka kujifunza kuchapa"


def test_normalize_profile_text_preserves_unicode_for_semantic_context():
    assert normalize_profile_text("A simple drawing app for kids") == "a simple drawing app for kids"
    assert normalize_profile_text("Kiswahili kwa watoto") == "kiswahili kwa watoto"


def test_build_semantic_profile_includes_optional_fields():
    entry = load_app_manifest(MANIFEST_PATH)[1]

    profile = build_semantic_profile(entry)

    assert "tux paint" in profile
    assert "paint program" in profile
    assert "picture" in profile


def test_build_semantic_profile_includes_new_app_aliases_and_tags():
    entry = _entry_by_app_id(load_app_manifest(MANIFEST_PATH), "scratch")

    profile = build_semantic_profile(entry)

    assert "cod for kids" in profile
    assert "program" in profile
    assert "game" in profile


def test_query_token_set_returns_unique_normalized_query_terms():
    assert query_token_set("what does plants eat?") == frozenset({"what", "does", "plants", "eat"})


def test_compute_lexical_overlap_score_rewards_token_overlap_and_priority_terms():
    query_tokens = query_token_set("what does plants eat?")
    profile_tokens = frozenset({"biology", "plant", "animal", "nature"})
    priority_tokens = frozenset({"plant", "animal"})

    score = compute_lexical_overlap_score(query_tokens, profile_tokens, priority_tokens)

    assert score > 0.0
    assert score <= 1.0


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
