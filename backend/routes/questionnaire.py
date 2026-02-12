from __future__ import annotations

import json

from flask import jsonify, request

from ..extensions import db
from ..models import QuestionnaireResponse
from ..utils import login_required
from . import questionnaire_bp


@questionnaire_bp.get("/questionnaire/me")
@login_required
def get_questionnaire(user):
    """Return the latest questionnaire entry for the logged-in user."""
    entry = (
        QuestionnaireResponse.query.filter_by(user_id=user.id)
        .order_by(QuestionnaireResponse.created_at.desc())
        .first()
    )
    if not entry:
        return jsonify({"error": "No questionnaire response found."}), 404
    return jsonify({"questionnaire": entry.to_dict()}), 200


@questionnaire_bp.post("/questionnaire/me")
@login_required
def save_questionnaire(user):
    """Save a questionnaire response for the logged-in user."""
    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers")
    recommendation_text = (payload.get("recommendation_text") or "").strip() or None

    if not isinstance(answers, dict) or not answers:
        return jsonify({"error": "Answers must be a non-empty object."}), 400

    try:
        answers_json = json.dumps(answers)
    except (TypeError, ValueError):
        return jsonify({"error": "Answers must be JSON serializable."}), 400

    entry = QuestionnaireResponse(
        user_id=user.id,
        answers_json=answers_json,
        recommendation_text=recommendation_text,
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({"questionnaire": entry.to_dict()}), 201
