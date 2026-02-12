from __future__ import annotations

from flask import jsonify, request

from ..extensions import db
from ..models import Progress
from ..utils import login_required
from . import progress_bp

PROGRESS_MAX = 10


@progress_bp.get("/progress")
@login_required
def list_progress(user):
    """Return the recorded learning milestones for the logged-in user."""
    entries = (
        Progress.query.filter_by(user_id=user.id)
        .order_by(Progress.created_at.desc())
        .all()
    )
    current = min(len(entries), PROGRESS_MAX)
    return jsonify(
        {
            "progress": [entry.to_dict() for entry in entries],
            "current": current,
            "max": PROGRESS_MAX,
        }
    )


@progress_bp.post("/progress")
@login_required
def add_progress(user):
    """Persist a new learning milestone for the user."""
    payload = request.get_json(silent=True) or {}
    milestone = (payload.get("milestone") or "").strip()
    notes = (payload.get("notes") or "").strip() or None

    if not milestone:
        return jsonify({"error": "Milestone is required"}), 400

    entry = Progress(user_id=user.id, milestone=milestone, notes=notes)
    db.session.add(entry)
    db.session.commit()

    return jsonify({"progress": entry.to_dict()}), 201


@progress_bp.post("/progress/increment")
@login_required
def increment_progress(user):
    """Increment progress by creating a capped milestone entry."""
    current = Progress.query.filter_by(user_id=user.id).count()
    if current >= PROGRESS_MAX:
        return jsonify({"current": PROGRESS_MAX, "max": PROGRESS_MAX, "capped": True}), 200

    milestone = f"Step {current + 1}"
    entry = Progress(user_id=user.id, milestone=milestone, notes=None)
    db.session.add(entry)
    db.session.commit()

    return (
        jsonify(
            {
                "current": min(current + 1, PROGRESS_MAX),
                "max": PROGRESS_MAX,
                "progress": entry.to_dict(),
            }
        ),
        201,
    )
