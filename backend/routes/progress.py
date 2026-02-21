from __future__ import annotations

from flask import jsonify, request

from ..extensions import db
from ..models import Progress
from ..utils import error_response, login_required
from . import progress_bp


@progress_bp.get("/progress")
@login_required
def list_progress(user):
    """Return the recorded learning milestones for the logged-in user."""
    entries = (
        Progress.query.filter_by(user_id=user.id)
        .order_by(Progress.created_at.desc())
        .all()
    )
    return jsonify({"progress": [entry.to_dict() for entry in entries]})


@progress_bp.post("/progress")
@login_required
def add_progress(user):
    """Persist a new learning milestone for the user."""
    payload = request.get_json(silent=True) or {}
    milestone = (payload.get("milestone") or "").strip()
    notes = (payload.get("notes") or "").strip() or None

    if not milestone:
        return error_response("Milestone is required", 400)

    entry = Progress(user_id=user.id, milestone=milestone, notes=notes)
    db.session.add(entry)
    db.session.commit()

    return jsonify({"progress": entry.to_dict()}), 201
