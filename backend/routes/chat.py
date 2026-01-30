from __future__ import annotations

from flask import jsonify, request

from ..extensions import db
from ..models import Message
from ..services.assistant import generate_assistant_reply
from ..utils import login_required
from . import chat_bp


@chat_bp.get("/chat/history")
@login_required
def history(user):
    """Return recent chat history for the authenticated user."""
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))

    chat_entries = (
        Message.query.filter_by(user_id=user.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    ordered = list(reversed(chat_entries))
    return jsonify({"history": [item.to_dict() for item in ordered]})


@chat_bp.post("/chat/message")
@login_required
def chat_message(user):
    """Persist a user message and return an assistant reply."""
    payload = request.get_json(silent=True) or {}
    message_text = (payload.get("text") or "").strip()
    if not message_text:
        return jsonify({"error": "Message text is required"}), 400

    user_entry = Message(user_id=user.id, role="user", content=message_text)
    db.session.add(user_entry)
    db.session.flush()

    reply_text = generate_assistant_reply(message_text, user_name=user.full_name)

    assistant_entry = Message(user_id=user.id, role="assistant", content=reply_text)
    db.session.add(assistant_entry)
    db.session.commit()

    return (
        jsonify(
            {
                "messages": [user_entry.to_dict(), assistant_entry.to_dict()],
            }
        ),
        201,
    )


@chat_bp.post("/chat/reset")
@login_required
def reset_chat(user):
    """Delete all messages for the authenticated user."""
    Message.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({"ok": True})
