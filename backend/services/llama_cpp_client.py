from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

LLAMA_CPP_BASE_URL = os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_CPP_CHAT_URL = f"{LLAMA_CPP_BASE_URL}/v1/chat/completions"
LLAMA_CPP_MODELS_URL = f"{LLAMA_CPP_BASE_URL}/v1/models"
DEFAULT_MODEL = os.getenv("LLAMA_CPP_MODEL_ALIAS", "local-model")
try:
    DEFAULT_MAX_ATTEMPTS = max(1, int(os.getenv("LLAMA_CPP_MAX_ATTEMPTS", "3")))
except ValueError:
    DEFAULT_MAX_ATTEMPTS = 3


class LlamaCppError(RuntimeError):
    """Raised when the local llama.cpp service cannot fulfill a generation request."""

    def __init__(
        self,
        message: str,
        *,
        reason: Optional[str] = None,
        status: Optional[int] = None,
        payload: Optional[dict] = None,
    ):
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
    """Send a prompt to the local llama.cpp server and return the generated text."""

    messages = []
    if system and system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if options:
        payload.update(options)

    logger.debug(
        "llama.cpp request prepared model=%s system=%s prompt_chars=%s options=%s",
        payload.get("model"),
        bool(system and system.strip()),
        len(prompt),
        bool(options),
    )

    attempts = max(1, max_attempts)
    last_exception: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(LLAMA_CPP_CHAT_URL, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_exception = exc
            logger.error("llama.cpp request failed (attempt %s/%s): %s", attempt, attempts, exc)
            if attempt == attempts:
                raise LlamaCppError(
                    "Could not reach the local llama.cpp model",
                    reason=str(exc),
                ) from exc
            time.sleep(min(2 * attempt, 5))
            continue

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("Invalid JSON from llama.cpp: %s", exc)
            raise LlamaCppError("Unexpected response from local AI service", reason="invalid_json") from exc

        if not response.ok:
            reason = data.get("error") if isinstance(data, dict) else response.text
            if isinstance(reason, dict):
                reason = reason.get("message") or str(reason)
            status = response.status_code
            message = (
                "Requested llama.cpp model is unavailable"
                if status == 404
                else "llama.cpp returned an error"
            )
            raise LlamaCppError(
                message,
                reason=reason,
                status=status,
                payload=data if isinstance(data, dict) else None,
            )

        result = _extract_content(data)
        if not result:
            logger.warning("llama.cpp returned an empty response for model %s", model)
            raise LlamaCppError("llama.cpp returned an empty response", reason="empty_response")

        return result

    raise LlamaCppError("Local AI service is unavailable", reason=str(last_exception) if last_exception else None)


def check_llama_cpp_health(timeout: int = 5) -> Dict[str, Any]:
    """Verify llama.cpp availability by reading the local model list."""
    try:
        response = requests.get(LLAMA_CPP_MODELS_URL, timeout=timeout)
    except requests.RequestException as exc:
        logger.error("llama.cpp health check failed: %s", exc)
        raise LlamaCppError("Unable to reach llama.cpp", reason=str(exc)) from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("Invalid JSON from llama.cpp health check: %s", exc)
        raise LlamaCppError("Unexpected response from llama.cpp", reason="invalid_json") from exc

    if not response.ok:
        reason = data.get("error") if isinstance(data, dict) else response.text
        if isinstance(reason, dict):
            reason = reason.get("message") or str(reason)
        raise LlamaCppError(
            "llama.cpp health endpoint returned an error",
            reason=reason,
            status=response.status_code,
            payload=data if isinstance(data, dict) else None,
        )

    models = [item.get("id") for item in data.get("data", []) if item.get("id")]
    return {"models": models, "base_url": LLAMA_CPP_BASE_URL}


def _extract_content(data: Dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""

    content = message.get("content", "")
    if isinstance(content, list):
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        content = "".join(text_parts)

    if not isinstance(content, str):
        return ""
    return content.strip()
