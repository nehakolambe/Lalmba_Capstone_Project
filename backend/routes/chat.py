from __future__ import annotations

import logging

from flask import jsonify, request
from flask import current_app

from ..extensions import db
from ..models import Message, Progress
from ..services.assistant import generate_assistant_reply, generate_hidden_summary
from ..services.app_search import AppMatch, search_apps
from ..services.conversation_state import (
    SUMMARY_WINDOW_TURNS,
    get_or_create_conversation_state,
    load_recent_completed_turns,
    load_turns_since_last_summary,
    reset_conversation_state,
)
from ..services.llama_cpp_client import LlamaCppError
from ..services.prompts import MatchedAppContext
from ..utils import error_response, login_required
from . import chat_bp

logger = logging.getLogger(__name__)


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
        return error_response("Message text is required", 400)

    conversation = get_or_create_conversation_state(user.id)
    has_previous_assistant_message = (
        Message.query.filter_by(user_id=user.id, role="assistant").first() is not None
    )
    summary_checkpoint_ran = False

    if conversation.turns_since_last_summary >= SUMMARY_WINDOW_TURNS:
        turns_to_summarize = load_recent_completed_turns(user.id, SUMMARY_WINDOW_TURNS)
        try:
            summary_text = generate_hidden_summary(turns_to_summarize)
        except LlamaCppError as exc:
            logger.exception("Hidden summarization failed for user %s", user.id)
            db.session.rollback()
            return error_response(
                "I’m having trouble updating conversation memory right now. Please try again in a moment.",
                503,
                details={"reason": getattr(exc, "reason", None)},
            )

        logger.info("Generated hidden summary for user %s: %s", user.id, summary_text)

        # Keep summary text and counter reset in one write transaction.
        conversation.current_summary = summary_text
        conversation.turns_since_last_summary = 0
        db.session.commit()
        summary_checkpoint_ran = True
        conversation = get_or_create_conversation_state(user.id)

    matched_app = _find_matched_app(message_text)
    overlap_turns, recent_turns = load_turns_since_last_summary(
        user.id,
        conversation=conversation,
    )
    try:
        reply_text = generate_assistant_reply(
            message_text,
            user_name=user.full_name,
            is_first_turn=not has_previous_assistant_message,
            matched_app=matched_app,
            current_summary=conversation.current_summary,
            overlap_turns=overlap_turns,
            recent_turns=recent_turns,
        )
    except LlamaCppError as exc:
        logger.exception("Assistant reply generation failed for user %s", user.id)
        db.session.rollback()
        return error_response(
            "I’m having trouble reaching the local AI model right now. Please try again in a moment.",
            503,
            details={"reason": getattr(exc, "reason", None)},
        )

    user_entry = Message(user_id=user.id, role="user", content=message_text)
    assistant_entry = Message(user_id=user.id, role="assistant", content=reply_text)
    db.session.add(user_entry)
    db.session.add(assistant_entry)
    conversation.turns_since_last_summary += 1
    db.session.commit()

    return (
        jsonify(
            {
                "messages": [user_entry.to_dict(), assistant_entry.to_dict()],
                "summary_checkpoint_ran": summary_checkpoint_ran,
            }
        ),
        201,
    )


@chat_bp.post("/chat/reset")
@login_required
def reset_chat(user):
    """Delete all messages AND progress for the authenticated user."""
    Message.query.filter_by(user_id=user.id).delete()
    Progress.query.filter_by(user_id=user.id).delete()
    reset_conversation_state(user.id)
    db.session.commit()
    return jsonify({"ok": True})


def _find_matched_app(message_text: str) -> MatchedAppContext | None:
    """Look up the best matching local app for a user message."""
    try:
        match = search_apps(current_app, message_text)
    except Exception:
        logger.exception("App search failed; continuing without app context")
        return None

    if match is None:
        logger.debug("No app match found for current user message")
        return None

    logger.info(
        "Matched app %s (%s) with score %.3f",
        match.app.app_id,
        match.app.name,
        match.score,
    )
    return _build_matched_app_context(match)


def _build_matched_app_context(match: AppMatch) -> MatchedAppContext:
    return MatchedAppContext(
        app_id=match.app.app_id,
        name=match.app.name,
        description=match.app.description,
        score=match.score,
    )
