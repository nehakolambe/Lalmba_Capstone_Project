from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class AppManifestError(ValueError):
    """Raised when the local app manifest is missing or invalid."""


@dataclass(frozen=True)
class AppManifestEntry:
    app_id: str
    name: str
    description: str
    tutorial_steps: tuple[str, ...]


def load_app_manifest(path: str | Path) -> list[AppManifestEntry]:
    """Load and validate the local app manifest JSON file."""
    manifest_path = Path(path)

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AppManifestError(f"App manifest file not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise AppManifestError(f"App manifest is not valid JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise AppManifestError("App manifest root must be a JSON array")

    entries: list[AppManifestEntry] = []
    for index, raw_entry in enumerate(payload):
        entries.append(_validate_entry(raw_entry, index))

    return entries


def _validate_entry(raw_entry: object, index: int) -> AppManifestEntry:
    if not isinstance(raw_entry, dict):
        raise AppManifestError(f"App manifest entry {index} must be an object")

    app_id = _require_non_empty_string(raw_entry, "app_id", index)
    name = _require_non_empty_string(raw_entry, "name", index)
    description = _require_non_empty_string(raw_entry, "description", index)
    tutorial_steps = _require_steps(raw_entry, index)

    return AppManifestEntry(
        app_id=app_id,
        name=name,
        description=description,
        tutorial_steps=tuple(tutorial_steps),
    )


def _require_non_empty_string(raw_entry: dict[str, object], field: str, index: int) -> str:
    value = raw_entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AppManifestError(
            f"App manifest entry {index} field '{field}' must be a non-empty string"
        )
    return value.strip()


def _require_steps(raw_entry: dict[str, object], index: int) -> list[str]:
    steps = raw_entry.get("tutorial_steps")
    if not isinstance(steps, list) or not steps:
        raise AppManifestError(
            f"App manifest entry {index} field 'tutorial_steps' must be a non-empty array"
        )

    cleaned_steps: list[str] = []
    for step_index, step in enumerate(steps):
        if not isinstance(step, str) or not step.strip():
            raise AppManifestError(
                "App manifest entry "
                f"{index} tutorial_steps[{step_index}] must be a non-empty string"
            )
        cleaned_steps.append(step.strip())
    return cleaned_steps
