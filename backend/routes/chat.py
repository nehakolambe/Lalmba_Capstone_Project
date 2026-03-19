from __future__ import annotations

import logging

from flask import current_app, jsonify, request

from ..extensions import db
from ..models import Message, Progress
from ..services.assistant import generate_assistant_reply, generate_conversation_summary
from ..services.app_search import AppMatch, search_apps
from ..services.chat_memory import get_chat_memory
from ..services.conversation_state import (
    build_session_metadata,
    get_or_create_conversation_state,
    load_turns_since_last_summary,
    reset_conversation_state,
    should_refresh_summary,
    summary_overlap_turns,
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
    conversation = get_or_create_conversation_state(user.id)
    return jsonify(
        {
            "history": [item.to_dict() for item in ordered],
            "session": _session_payload(conversation),
        }
    )


@chat_bp.post("/chat/message")
@login_required
def chat_message(user):
    """Persist a user message and return an assistant reply."""
    payload = request.get_json(silent=True) or {}
    message_text = (payload.get("text") or "").strip()
    if not message_text:
        return error_response("Message text is required", 400)

    conversation = get_or_create_conversation_state(user.id)
    if (
        conversation.question_count >= current_app.config["CHAT_QUESTION_LIMIT"]
    ):
        return jsonify(
            {
                "messages": [_build_ephemeral_assistant_message(_question_limit_message())],
                "session": _session_payload(conversation),
            }
        ), 200

    has_previous_assistant_message = (
        Message.query.filter_by(user_id=user.id, role="assistant").first() is not None
    )
    matched_app = _find_matched_app(message_text)
    surfaced_app = _maybe_surface_app_suggestion(conversation, message_text, matched_app)

    chat_memory = get_chat_memory(current_app)
    retrieval = None
    if chat_memory is not None:
        retrieval = chat_memory.retrieve_context(user.id, message_text)

    try:
        reply_text = generate_assistant_reply(
            message_text,
            user_name=user.full_name,
            is_first_turn=not has_previous_assistant_message,
            conversation_summary=conversation.current_summary,
            matched_app=surfaced_app,
            retrieved_background=[] if retrieval is None else retrieval.anchors,
            recent_turns=[] if retrieval is None else retrieval.recent_turns,
            user_id=user.id,
            prompt_log=None
            if retrieval is None
            else {
                "chroma_matches": retrieval.matches_returned,
                "threshold_matches": retrieval.matches_after_threshold,
                "budget_matches": retrieval.matches_after_budget,
                "background_chars": retrieval.background_chars,
                "fifo_turns": len(retrieval.recent_turns),
                "app_context": surfaced_app is not None,
            },
        )
    except LlamaCppError as exc:
        logger.exception("Assistant reply generation failed for user %s", user.id)
        db.session.rollback()
        return error_response(
            "I’m having trouble reaching the local AI model right now. Please try again in a moment.",
            503,
            details={"reason": getattr(exc, "reason", None)},
        )

    return _persist_tutor_exchange(
        user=user,
        conversation=conversation,
        visible_user_text=message_text,
        tutor_query_text=message_text,
        assistant_text=reply_text,
        chat_memory=chat_memory,
        surfaced_app=surfaced_app,
    )


@chat_bp.post("/chat/reset")
@login_required
def reset_chat(user):
    """Delete all messages AND progress for the authenticated user."""
    Message.query.filter_by(user_id=user.id).delete()
    Progress.query.filter_by(user_id=user.id).delete()
    reset_conversation_state(user.id)

    chat_memory = get_chat_memory(current_app)
    if chat_memory is not None:
        chat_memory.clear_user(user.id)

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
        start_step=match.app.tutorial_steps[0] if match.app.tutorial_steps else None,
    )


def _persist_tutor_exchange(
    *,
    user,
    conversation,
    visible_user_text: str,
    tutor_query_text: str,
    assistant_text: str,
    chat_memory,
    surfaced_app: MatchedAppContext | None,
):
    user_entry, assistant_entry = _build_exchange_entries(user.id, visible_user_text, assistant_text)
    db.session.add(user_entry)
    db.session.add(assistant_entry)
    conversation.turns_since_last_summary += 1
    conversation.question_count += 1
    _remember_app_suggestion(conversation, visible_user_text, surfaced_app)

    archive_doc_id: str | None = None
    try:
        if should_refresh_summary(conversation):
            _refresh_summary(user.id, conversation)
        if chat_memory is not None:
            archive_doc_id = chat_memory.archive_turn(
                user_id=user.id,
                query_text=tutor_query_text,
                response_text=assistant_text,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        if chat_memory is not None and archive_doc_id is not None:
            try:
                chat_memory.delete_archive_doc(archive_doc_id)
            except Exception:
                logger.exception("Failed to roll back archived turn %s", archive_doc_id)
        logger.exception("Post-generation persistence failed for user %s", user.id)
        return error_response(
            "I’m having trouble saving conversation memory right now. Please try again in a moment.",
            503,
        )

    if chat_memory is not None:
        chat_memory.append_recent_turn(user.id, tutor_query_text, assistant_text)

    return (
        jsonify(
            {
                "messages": [user_entry.to_dict(), assistant_entry.to_dict()],
                "session": _session_payload(conversation),
            }
        ),
        201,
    )


def _refresh_summary(user_id: int, conversation) -> None:
    overlap_turns, recent_turns = load_turns_since_last_summary(
        user_id,
        overlap_turns=summary_overlap_turns(),
        conversation=conversation,
    )
    summary = generate_conversation_summary(
        conversation.current_summary,
        [*overlap_turns, *recent_turns],
    )
    conversation.current_summary = summary or conversation.current_summary
    conversation.turns_since_last_summary = 0


def _build_exchange_entries(user_id: int, user_text: str, assistant_text: str) -> tuple[Message, Message]:
    return (
        Message(user_id=user_id, role="user", content=user_text),
        Message(user_id=user_id, role="assistant", content=assistant_text),
    )


def _build_ephemeral_assistant_message(content: str) -> dict[str, str | None]:
    return {
        "id": None,
        "user_id": None,
        "role": "assistant",
        "content": content,
        "created_at": None,
    }


def _session_payload(conversation) -> dict[str, int | bool | str | None]:
    return build_session_metadata(conversation)


def _question_limit_message() -> str:
    question_limit = current_app.config.get("CHAT_QUESTION_LIMIT", 10)
    return (
        f"You have reached the {question_limit}-question limit for this chat. "
        "Please reset the session to start a new lesson."
    )


def _maybe_surface_app_suggestion(
    conversation,
    message_text: str,
    matched_app: MatchedAppContext | None,
) -> MatchedAppContext | None:
    if matched_app is None:
        return None
    if _looks_like_explicit_app_request(message_text):
        return matched_app

    current_hint = _derive_topic_hint(message_text, matched_app)
    if (
        conversation.last_suggested_app_id == matched_app.app_id
        and conversation.last_app_topic_hint == current_hint
    ):
        return None
    return matched_app


def _remember_app_suggestion(
    conversation,
    message_text: str,
    surfaced_app: MatchedAppContext | None,
) -> None:
    if surfaced_app is None:
        return
    conversation.last_suggested_app_id = surfaced_app.app_id
    conversation.last_app_topic_hint = _derive_topic_hint(message_text, surfaced_app)


def _derive_topic_hint(message_text: str, matched_app: MatchedAppContext | None) -> str:
    normalized = " ".join((message_text or "").strip().lower().split())
    if matched_app is None:
        return normalized[:255]
    if matched_app.app_id == "tux_math":
        return "math-practice"
    if matched_app.app_id == "tux_paint":
        return "drawing-art"
    if matched_app.app_id == "tux_typing":
        return "typing-keyboard"
    return f"{matched_app.app_id}:{normalized[:180]}"


def _looks_like_explicit_app_request(message_text: str) -> bool:
    normalized = " ".join((message_text or "").strip().lower().split())
    explicit_terms = (
        "app",
        "game",
        "software",
        "program",
        "tool",
        "use ",
        "open ",
        "launch ",
    )
    return any(term in normalized for term in explicit_terms)
