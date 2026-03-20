from __future__ import annotations

from flask import jsonify, request

from ..extensions import db
from ..models import Progress
from ..services.chat_threads import get_or_create_default_thread, get_thread
from ..utils import error_response, login_required
from . import progress_bp


@progress_bp.get("/progress")
@login_required
def list_progress(user):
    """Return the recorded learning milestones for the logged-in user."""
    thread = _resolve_thread(user.id)
    entries = (
        Progress.query.filter_by(user_id=user.id, thread_id=thread.id)
        .order_by(Progress.created_at.desc())
        .all()
    )
    return jsonify({"thread": thread.to_dict(), "progress": [entry.to_dict() for entry in entries]})


@progress_bp.post("/progress")
@login_required
def add_progress(user):
    """Persist a new learning milestone - max 10 per user."""
    payload = request.get_json(silent=True) or {}
    thread = _resolve_thread(user.id, payload)
    existing_count = Progress.query.filter_by(user_id=user.id, thread_id=thread.id).count()
    if existing_count >= 10:
        return jsonify({"progress": None}), 200

    milestone = (payload.get("milestone") or "").strip()
    notes = (payload.get("notes") or "").strip() or None

    if not milestone:
        return error_response("Milestone is required", 400)

    entry = Progress(
        user_id=user.id,
        thread_id=thread.id,
        milestone=milestone,
        notes=notes,
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify({"progress": entry.to_dict()}), 201


@progress_bp.post("/progress/reset")
@login_required
def reset_progress(user):
    """Delete only progress bar entries - chat history untouched."""
    thread = _resolve_thread(user.id, request.get_json(silent=True) or {})
    Progress.query.filter_by(user_id=user.id, thread_id=thread.id).delete()
    db.session.commit()
    return jsonify({"ok": True})


def _resolve_thread(user_id: int, payload: dict | None = None):
    raw_value = request.args.get("thread_id") if payload is None else payload.get("thread_id")
    try:
        thread_id = int(raw_value) if raw_value not in (None, "") else None
    except (TypeError, ValueError):
        thread_id = None
    thread = get_thread(user_id, thread_id) if thread_id is not None else None
    return thread or get_or_create_default_thread(user_id)
