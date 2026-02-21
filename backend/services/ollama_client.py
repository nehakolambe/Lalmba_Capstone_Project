from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/").rstrip("/")
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_HEALTH_URL = f"{OLLAMA_BASE_URL}/api/tags"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
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


def generate_response(
    prompt: str,
    *,
    system: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    options: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """Send a prompt to the local Ollama instance and return the generated text."""

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,  # easier to consume in a web backend
    }
    if system and system.strip():
        payload["system"] = system.strip()
    if options:
        payload["options"] = options

    # Debug output so prompt content is visible during local development/tests.
    print("\n--- OLLAMA REQUEST PAYLOAD ---")
    print(f"model: {payload.get('model')}")
    print(f"system: {payload.get('system', '')}")
    print(f"prompt: {payload.get('prompt', '')}")
    print("--- END OLLAMA REQUEST PAYLOAD ---\n")

    attempts = max(1, max_attempts)
    last_exception: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_exception = exc
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
