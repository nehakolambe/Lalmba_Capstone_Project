from __future__ import annotations

import pytest
import requests

from backend.services.llama_cpp_client import (
    LlamaCppError,
    check_llama_cpp_health,
    generate_response,
    generate_response_stream,
)


class _FakeResponse:
    def __init__(self, payload, *, ok=True, status_code=200, text=""):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def iter_lines(self, decode_unicode=True):
        if isinstance(self._payload, list):
            yield from self._payload
            return
        return iter(())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_generate_response_parses_chat_completion(monkeypatch):
    captured = {}

    def _fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "Helpful answer from llama.cpp",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.post", _fake_post)

    result = generate_response("What should I study?", system="You are helpful.", options={"temperature": 0.2})

    assert result == "Helpful answer from llama.cpp"
    assert captured["timeout"] == 60
    assert captured["json"]["model"] == "local-model"
    assert captured["json"]["stream"] is False
    assert captured["json"]["temperature"] == 0.2
    assert captured["json"]["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert captured["json"]["messages"][1] == {"role": "user", "content": "What should I study?"}


def test_generate_response_retries_then_raises(monkeypatch):
    attempts = {"count": 0}

    def _fake_post(url, json, timeout):
        attempts["count"] += 1
        raise requests.RequestException("connection refused")

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.post", _fake_post)
    monkeypatch.setattr("backend.services.llama_cpp_client.time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(LlamaCppError) as exc_info:
        generate_response("Hello", max_attempts=2)

    assert attempts["count"] == 2
    assert "Could not reach the local llama.cpp model" in str(exc_info.value)
    assert "connection refused" in exc_info.value.reason


def test_generate_response_surfaces_http_errors(monkeypatch):
    def _fake_post(url, json, timeout):
        return _FakeResponse(
            {"error": {"message": "model not loaded"}},
            ok=False,
            status_code=503,
        )

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.post", _fake_post)

    with pytest.raises(LlamaCppError) as exc_info:
        generate_response("Hello")

    assert str(exc_info.value) == "llama.cpp returned an error"
    assert exc_info.value.status == 503
    assert exc_info.value.reason == "model not loaded"


def test_generate_response_rejects_empty_content(monkeypatch):
    def _fake_post(url, json, timeout):
        return _FakeResponse({"choices": [{"message": {"content": "   "}}]})

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.post", _fake_post)

    with pytest.raises(LlamaCppError) as exc_info:
        generate_response("Hello")

    assert str(exc_info.value) == "llama.cpp returned an empty response"
    assert exc_info.value.reason == "empty_response"


def test_generate_response_stream_yields_deltas(monkeypatch):
    captured = {}

    def _fake_post(url, json, timeout, stream):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        captured["stream"] = stream
        return _FakeResponse(
            [
                'data: {"choices":[{"delta":{"content":"Hello"}}]}',
                'data: {"choices":[{"delta":{"content":" there"}}]}',
                'data: [DONE]',
            ]
        )

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.post", _fake_post)

    result = list(generate_response_stream("What should I study?", system="You are helpful."))

    assert result == ["Hello", " there"]
    assert captured["timeout"] == 60
    assert captured["stream"] is True
    assert captured["json"]["stream"] is True
    assert captured["json"]["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert captured["json"]["messages"][1] == {"role": "user", "content": "What should I study?"}


def test_generate_response_stream_raises_on_empty_response(monkeypatch):
    def _fake_post(url, json, timeout, stream):
        return _FakeResponse(['data: [DONE]'])

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.post", _fake_post)

    with pytest.raises(LlamaCppError) as exc_info:
        list(generate_response_stream("Hello"))

    assert str(exc_info.value) == "llama.cpp returned an empty response"
    assert exc_info.value.reason == "empty_response"


def test_check_llama_cpp_health_returns_models(monkeypatch):
    def _fake_get(url, timeout):
        return _FakeResponse({"data": [{"id": "local-model"}, {"id": "backup-model"}]})

    monkeypatch.setattr("backend.services.llama_cpp_client.requests.get", _fake_get)

    result = check_llama_cpp_health()

    assert result["models"] == ["local-model", "backup-model"]
    assert result["base_url"] == "http://127.0.0.1:8080"
