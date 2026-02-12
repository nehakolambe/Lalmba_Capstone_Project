from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure the package is importable when running `python questionnaire.py`.
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import create_app
from backend.extensions import db
from backend.models import QuestionnaireResponse, User


def _ask(prompt: str, *, required: bool = False) -> str:
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("Please enter a value.")


def _collect_answers() -> Dict[str, Any]:
    questions = [
        {
            "key": "age_range",
            "prompt": "Age range (e.g., 12-18, 19-30, 31-45, 46+): ",
            "required": True,
        },
        {
            "key": "language_preference",
            "prompt": "Preferred language for learning (e.g., English, Kiswahili): ",
            "required": True,
        },
        {
            "key": "literacy_level",
            "prompt": "Reading comfort (low/medium/high): ",
            "required": True,
        },
        {
            "key": "typing_comfort",
            "prompt": "Typing comfort (low/medium/high): ",
            "required": True,
        },
        {
            "key": "business_interest",
            "prompt": "Do you run or want to start a business? (yes/no/unsure): ",
            "required": True,
        },
        {
            "key": "learning_goals",
            "prompt": "What topics do you want to learn most right now? ",
            "required": True,
        },
        {
            "key": "weekly_time",
            "prompt": "How many hours per week can you spend learning? ",
            "required": True,
        },
        {
            "key": "device_access",
            "prompt": "Primary device (laptop/phone/both): ",
            "required": True,
        },
        {
            "key": "prior_experience",
            "prompt": "Prior experience with computers (none/basics/intermediate/advanced): ",
            "required": True,
        },
        {
            "key": "additional_notes",
            "prompt": "Any accessibility needs or other notes (optional): ",
            "required": False,
        },
    ]

    answers: Dict[str, Any] = {}
    for item in questions:
        answers[item["key"]] = _ask(item["prompt"], required=item["required"])

    answers["submitted_at"] = datetime.now(timezone.utc).isoformat()
    return answers


def _generate_recommendation(answers: Dict[str, Any]) -> Optional[str]:
    try:
        from backend.services.ollama_client import OllamaError, generate_response
    except Exception as exc:
        print(f"Ollama client unavailable: {exc}")
        return None

    prompt = (
        "You are a learning coach. Based on the learner profile below, "
        "write a concise recommended learning path (1-2 short paragraphs). "
        "Keep the tone friendly and practical.\n\n"
        f"Profile JSON:\n{json.dumps(answers, indent=2)}\n\n"
        "Recommendation:"
    )
    try:
        return generate_response(prompt)
    except OllamaError as exc:
        print(f"Ollama evaluation failed: {getattr(exc, 'reason', str(exc))}")
    except Exception as exc:
        print(f"Ollama evaluation failed: {exc}")
    return None


def _save_to_db(username: str, answers: Dict[str, Any], recommendation_text: Optional[str]) -> QuestionnaireResponse:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).one_or_none()
        if not user:
            raise LookupError(f"User '{username}' not found in database.")
        entry = QuestionnaireResponse(
            user_id=user.id,
            answers_json=json.dumps(answers),
            recommendation_text=recommendation_text,
        )
        db.session.add(entry)
        db.session.commit()
        return entry


def _save_to_json(username: str, answers: Dict[str, Any], recommendation_text: Optional[str]) -> Path:
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = data_dir / f"questionnaire_{username}_{timestamp}.json"
    payload = {
        "username": username,
        "answers": answers,
        "recommendation_text": recommendation_text,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect onboarding questionnaire responses.")
    parser.add_argument("--username", required=True, help="Existing username in the system")
    parser.add_argument("--use-ollama", action="store_true", help="Generate a local recommendation via Ollama")
    args = parser.parse_args()

    print("Matoso onboarding questionnaire")
    print("--------------------------------")
    answers = _collect_answers()

    recommendation_text = None
    if args.use_ollama:
        print("\nGenerating a short learning path recommendation...")
        recommendation_text = _generate_recommendation(answers)

    try:
        entry = _save_to_db(args.username, answers, recommendation_text)
        print("\nSaved questionnaire to SQLite.")
        print(f"User ID: {entry.user_id}")
        print(f"Response ID: {entry.id}")
        print(f"Created at: {entry.created_at.isoformat()}")
        if entry.recommendation_text:
            print("\nRecommendation:\n" + entry.recommendation_text)
    except Exception as exc:
        print(f"\nDatabase save failed: {exc}")
        path = _save_to_json(args.username, answers, recommendation_text)
        print(f"Saved questionnaire to JSON: {path}")

    print("\nAnswers:")
    print(json.dumps(answers, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
