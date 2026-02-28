from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_HEALTH_URL = f"{OLLAMA_BASE_URL}/api/tags"
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama2")
try:
    DEFAULT_TIMEOUT_SECONDS = max(10, int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")))
except ValueError:
    DEFAULT_TIMEOUT_SECONDS = 120
try:
    DEFAULT_MAX_ATTEMPTS = max(1, int(os.getenv("OLLAMA_MAX_ATTEMPTS", "3")))
except ValueError:
    DEFAULT_MAX_ATTEMPTS = 3


class OllamaError(RuntimeError):
    """Raised when the Ollama service cannot fulfill a generation request."""

    def __init__(self, message: str, *, reason: Optional[str] = None, status: Optional[int] = None, payload: Optional[dict] = None):
        super().__init__(message)
        self.reason = reason
        self.status = status
        self.payload = payload or {}


def _select_fallback_model(unavailable_model: str) -> Optional[str]:
    try:
        health = check_ollama_health(timeout=5)
    except OllamaError as exc:
        logger.warning("Unable to fetch Ollama models for fallback: %s", exc)
        return None

    models = [name for name in health.get("models", []) if isinstance(name, str)]
    for name in models:
        if name != unavailable_model:
            return name
    return None


def generate_response(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    options: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """Send a prompt to the local Ollama instance and return the generated text."""

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,  # easier to consume in a web backend
    }
    if options:
        payload["options"] = options

    attempts = max(1, max_attempts)
    last_exception: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_exception = exc
            if isinstance(exc, requests.Timeout):
                logger.warning(
                    "Ollama request timed out (attempt %s/%s, timeout=%ss): %s",
                    attempt,
                    attempts,
                    timeout,
                    exc,
                )
            else:
                logger.error("Ollama request failed (attempt %s/%s): %s", attempt, attempts, exc)
            if attempt == attempts:
                raise OllamaError(
                    "Could not reach the local Ollama model",
                    reason=str(exc),
                ) from exc
            time.sleep(min(2 * attempt, 5))
            continue

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("Invalid JSON from Ollama: %s", exc)
            raise OllamaError("Unexpected response from local AI service", reason="invalid_json") from exc

        if not response.ok:
            reason = data.get("error") if isinstance(data, dict) else response.text
            status = response.status_code
            if status == 404:
                fallback_model = _select_fallback_model(model)
                if fallback_model and fallback_model != model:
                    logger.warning(
                        "Ollama model %s unavailable; retrying with %s",
                        model,
                        fallback_model,
                    )
                    fallback_payload = {**payload, "model": fallback_model}
                    try:
                        fallback_response = requests.post(
                            OLLAMA_GENERATE_URL,
                            json=fallback_payload,
                            timeout=timeout,
                        )
                    except requests.RequestException as exc:
                        last_exception = exc
                        logger.error("Ollama request failed (fallback): %s", exc)
                        raise OllamaError(
                            "Could not reach the local Ollama model",
                            reason=str(exc),
                        ) from exc

                    try:
                        fallback_data = fallback_response.json()
                    except ValueError as exc:
                        logger.error("Invalid JSON from Ollama: %s", exc)
                        raise OllamaError(
                            "Unexpected response from local AI service",
                            reason="invalid_json",
                        ) from exc

                    if not fallback_response.ok:
                        fallback_reason = (
                            fallback_data.get("error")
                            if isinstance(fallback_data, dict)
                            else fallback_response.text
                        )
                        raise OllamaError(
                            "Ollama returned an error",
                            reason=fallback_reason,
                            status=fallback_response.status_code,
                            payload=fallback_data if isinstance(fallback_data, dict) else None,
                        )

                    result = fallback_data.get("response", "")
                    if not result or not result.strip():
                        logger.warning(
                            "Ollama returned an empty response for model %s",
                            fallback_model,
                        )
                        raise OllamaError(
                            "Ollama returned an empty response",
                            reason="empty_response",
                        )

                    return result.strip()
            message = (
                "Requested Ollama model is unavailable"
                if status == 404
                else "Ollama returned an error"
            )
            raise OllamaError(message, reason=reason, status=status, payload=data if isinstance(data, dict) else None)

        result = data.get("response", "")
        if not result or not result.strip():
            logger.warning("Ollama returned an empty response for model %s", model)
            raise OllamaError("Ollama returned an empty response", reason="empty_response")

        return result.strip()

    raise OllamaError("Local AI service is unavailable", reason=str(last_exception) if last_exception else None)


def check_ollama_health(timeout: int = 5) -> Dict[str, Any]:
    """Verify Ollama availability by reading the local tags list."""
    # TIP: This hits /api/tags instead of /api/generate so it is fast and does not charge tokens.
    try:
        response = requests.get(OLLAMA_HEALTH_URL, timeout=timeout)
    except requests.RequestException as exc:
        logger.error("Ollama health check failed: %s", exc)
        raise OllamaError("Unable to reach Ollama", reason=str(exc)) from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("Invalid JSON from Ollama health check: %s", exc)
        raise OllamaError("Unexpected response from Ollama", reason="invalid_json") from exc

    if not response.ok:
        reason = data.get("error") if isinstance(data, dict) else response.text
        raise OllamaError(
            "Ollama health endpoint returned an error",
            reason=reason,
            status=response.status_code,
            payload=data if isinstance(data, dict) else None,
        )

    models = [item.get("name") for item in data.get("models", []) if item.get("name")]
    return {"models": models, "base_url": OLLAMA_BASE_URL}
