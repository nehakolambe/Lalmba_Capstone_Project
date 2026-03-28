from __future__ import annotations

import logging
import json

from flask import Response, current_app, jsonify, request, stream_with_context

from ..extensions import db
from ..models import ChatThread, Message, Progress
from ..services.assistant import (
    generate_assistant_reply,
    generate_conversation_summary,
    stream_assistant_reply,
)
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
from ..services.chat_threads import (
    build_auto_thread_title,
    create_thread,
    get_or_create_default_thread,
    get_thread,
    list_threads,
    normalize_thread_title,
    touch_thread,
)
from ..utils import error_response, login_required
from . import chat_bp

logger = logging.getLogger(__name__)


@chat_bp.get("/chat/history")
@login_required
def history(user):
    """Return recent chat history for the authenticated user."""
    thread = _resolve_thread_from_request(user.id)
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))

    chat_entries = (
        Message.query.filter_by(user_id=user.id, thread_id=thread.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    ordered = list(reversed(chat_entries))
    conversation = get_or_create_conversation_state(user.id, thread.id)
    return jsonify(
        {
            "thread": thread.to_dict(),
            "history": [item.to_dict() for item in ordered],
            "session": _session_payload(conversation),
        }
    )


@chat_bp.get("/chat/threads")
@login_required
def thread_list(user):
    """Return chat threads for the current user, creating one if needed."""
    get_or_create_default_thread(user.id)
    db.session.commit()
    return jsonify({"threads": [thread.to_dict() for thread in list_threads(user.id)]})


@chat_bp.post("/chat/threads")
@login_required
def create_chat_thread(user):
    """Create a new empty chat thread."""
    payload = request.get_json(silent=True) or {}
    thread = create_thread(user.id, title=payload.get("title"))
    db.session.commit()
    return jsonify({"thread": thread.to_dict()}), 201


@chat_bp.patch("/chat/threads/<int:thread_id>")
@login_required
def rename_chat_thread(user, thread_id: int):
    """Rename an existing chat thread."""
    thread = get_thread(user.id, thread_id)
    if thread is None:
        return error_response("Chat thread not found", 404)

    payload = request.get_json(silent=True) or {}
    title = normalize_thread_title(payload.get("title"))
    if not title.strip():
        return error_response("Chat title is required", 400)

    thread.title = title
    touch_thread(thread)
    db.session.commit()
    return jsonify({"thread": thread.to_dict()})


@chat_bp.delete("/chat/threads/<int:thread_id>")
@login_required
def delete_chat_thread(user, thread_id: int):
    """Delete a chat thread and all of its related state."""
    thread = get_thread(user.id, thread_id)
    if thread is None:
        return error_response("Chat thread not found", 404)

    chat_memory = get_chat_memory(current_app)
    if chat_memory is not None:
        chat_memory.clear_thread(user.id, thread.id)
    db.session.delete(thread)
    db.session.commit()
    return jsonify({"ok": True})


@chat_bp.post("/chat/message")
@login_required
def chat_message(user):
    """Persist a user message and return an assistant reply."""
    payload = request.get_json(silent=True) or {}
    message_text = (payload.get("text") or "").strip()
    if not message_text:
        return error_response("Message text is required", 400)

    context = _prepare_chat_generation(user, payload, message_text)
    if context["limit_response"] is not None:
        return jsonify(context["limit_response"]), 200

    try:
        reply_text = generate_assistant_reply(
            message_text,
            user_name=user.full_name,
            is_first_turn=context["is_first_turn"],
            conversation_summary=context["conversation"].current_summary,
            matched_app=context["surfaced_app"],
            retrieved_background=context["retrieved_background"],
            recent_turns=context["recent_turns"],
            user_id=user.id,
            prompt_log=context["prompt_log"],
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
        thread=context["thread"],
        conversation=context["conversation"],
        visible_user_text=message_text,
        tutor_query_text=message_text,
        assistant_text=reply_text,
        chat_memory=context["chat_memory"],
        surfaced_app=context["surfaced_app"],
    )


@chat_bp.post("/chat/message/stream")
@login_required
def chat_message_stream(user):
    """Persist a user message and stream the assistant reply."""
    payload = request.get_json(silent=True) or {}
    message_text = (payload.get("text") or "").strip()
    if not message_text:
        return error_response("Message text is required", 400)

    context = _prepare_chat_generation(user, payload, message_text)
    if context["limit_response"] is not None:
        return jsonify(context["limit_response"]), 200

    stream = stream_assistant_reply(
        message_text,
        user_name=user.full_name,
        is_first_turn=context["is_first_turn"],
        conversation_summary=context["conversation"].current_summary,
        matched_app=context["surfaced_app"],
        retrieved_background=context["retrieved_background"],
        recent_turns=context["recent_turns"],
        user_id=user.id,
        prompt_log=context["prompt_log"],
    )

    assistant_parts: list[str] = []
    try:
        first_chunk = next(stream)
    except StopIteration:
        return error_response(
            "I’m having trouble reaching the local AI model right now. Please try again in a moment.",
            503,
            details={"reason": "empty_response"},
        )
    except LlamaCppError as exc:
        logger.exception("Assistant streaming failed before first chunk for user %s", user.id)
        db.session.rollback()
        return error_response(
            "I’m having trouble reaching the local AI model right now. Please try again in a moment.",
            503,
            details={"reason": getattr(exc, "reason", None)},
        )

    assistant_parts.append(first_chunk)

    @stream_with_context
    def _event_stream():
        yield _ndjson_event({"type": "delta", "content": first_chunk})
        stream_failed = False
        try:
            for chunk in stream:
                assistant_parts.append(chunk)
                yield _ndjson_event({"type": "delta", "content": chunk})
        except LlamaCppError as exc:
            stream_failed = True
            logger.exception("Assistant streaming failed mid-stream for user %s", user.id)
            db.session.rollback()
            yield _ndjson_event(
                {
                    "type": "error",
                    "error": "I’m having trouble reaching the local AI model right now. Please try again in a moment.",
                    "details": {"reason": getattr(exc, "reason", None)},
                }
            )

        if stream_failed:
            return

        assistant_text = "".join(assistant_parts).strip()
        if not assistant_text:
            db.session.rollback()
            yield _ndjson_event(
                {
                    "type": "error",
                    "error": "I’m having trouble reaching the local AI model right now. Please try again in a moment.",
                    "details": {"reason": "empty_response"},
                }
            )
            return

        persist_result = _persist_tutor_exchange(
            user=user,
            thread=context["thread"],
            conversation=context["conversation"],
            visible_user_text=message_text,
            tutor_query_text=message_text,
            assistant_text=assistant_text,
            chat_memory=context["chat_memory"],
            surfaced_app=context["surfaced_app"],
        )

        if isinstance(persist_result, tuple):
            response, status = persist_result
            if status >= 400:
                data = response.get_json(silent=True) or {}
                yield _ndjson_event(
                    {
                        "type": "error",
                        "error": data.get("error")
                        or "I’m having trouble saving conversation memory right now. Please try again in a moment.",
                        "details": data.get("details"),
                    }
                )
                return
            body = response.get_json(silent=True) or {}
        else:
            body = persist_result.get_json(silent=True) or {}

        messages = body.get("messages") or []
        assistant_message = next(
            (entry for entry in messages if entry.get("role") == "assistant"),
            {"role": "assistant", "content": assistant_text},
        )
        yield _ndjson_event(
            {
                "type": "done",
                "thread": body.get("thread"),
                "message": assistant_message,
                "session": body.get("session"),
            }
        )

    return Response(_event_stream(), mimetype="application/x-ndjson")


@chat_bp.post("/chat/reset")
@login_required
def reset_chat(user):
    """Delete messages and progress for one chat thread."""
    payload = request.get_json(silent=True) or {}
    thread = _resolve_thread_from_payload(user.id, payload)
    Message.query.filter_by(user_id=user.id, thread_id=thread.id).delete()
    Progress.query.filter_by(user_id=user.id, thread_id=thread.id).delete()
    reset_conversation_state(user.id, thread.id)
    chat_memory = get_chat_memory(current_app)
    if chat_memory is not None:
        chat_memory.clear_thread(user.id, thread.id)
    touch_thread(thread)
    db.session.commit()
    return jsonify({"ok": True, "thread": thread.to_dict()})


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
        "Matched app %s (%s) with score %.3f (%.1f%% match)",
        match.app.app_id,
        match.app.name,
        match.score,
        match.score * 100.0,
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
    thread,
    conversation,
    visible_user_text: str,
    tutor_query_text: str,
    assistant_text: str,
    chat_memory,
    surfaced_app: MatchedAppContext | None,
):
    user_entry, assistant_entry = _build_exchange_entries(
        user.id,
        thread.id,
        visible_user_text,
        assistant_text,
    )
    db.session.add(user_entry)
    db.session.add(assistant_entry)
    conversation.turns_since_last_summary += 1
    conversation.question_count += 1
    if thread.title == "New chat":
        thread.title = build_auto_thread_title(visible_user_text)
    touch_thread(thread)
    _remember_app_suggestion(conversation, visible_user_text, surfaced_app)

    archive_doc_id: str | None = None
    try:
        if should_refresh_summary(conversation):
            _refresh_summary(user.id, thread.id, conversation)
        if chat_memory is not None:
            archive_doc_id = chat_memory.archive_turn(
                user_id=user.id,
                thread_id=thread.id,
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
        chat_memory.append_recent_turn(user.id, thread.id, tutor_query_text, assistant_text)

    return (
        jsonify(
            {
                "thread": thread.to_dict(),
                "messages": [user_entry.to_dict(), assistant_entry.to_dict()],
                "session": _session_payload(conversation),
            }
        ),
        201,
    )


def _refresh_summary(user_id: int, thread_id: int, conversation) -> None:
    overlap_turns, recent_turns = load_turns_since_last_summary(
        user_id,
        thread_id,
        overlap_turns=summary_overlap_turns(),
        conversation=conversation,
    )
    summary = generate_conversation_summary(
        conversation.current_summary,
        [*overlap_turns, *recent_turns],
    )
    conversation.current_summary = summary or conversation.current_summary
    conversation.turns_since_last_summary = 0


def _build_exchange_entries(
    user_id: int,
    thread_id: int,
    user_text: str,
    assistant_text: str,
) -> tuple[Message, Message]:
    return (
        Message(user_id=user_id, thread_id=thread_id, role="user", content=user_text),
        Message(user_id=user_id, thread_id=thread_id, role="assistant", content=assistant_text),
    )


def _build_ephemeral_assistant_message(content: str) -> dict[str, str | None]:
    return {
        "id": None,
        "user_id": None,
        "role": "assistant",
        "content": content,
        "created_at": None,
    }


def _ndjson_event(payload: dict) -> str:
    return f"{json.dumps(payload)}\n"


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


def _resolve_thread_id(raw_value) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _resolve_thread_from_request(user_id: int) -> ChatThread:
    requested_thread_id = _resolve_thread_id(request.args.get("thread_id"))
    thread = get_thread(user_id, requested_thread_id) if requested_thread_id else None
    return thread or get_or_create_default_thread(user_id)


def _resolve_thread_from_payload(user_id: int, payload: dict) -> ChatThread:
    requested_thread_id = _resolve_thread_id(payload.get("thread_id"))
    thread = get_thread(user_id, requested_thread_id) if requested_thread_id else None
    return thread or get_or_create_default_thread(user_id)


def _prepare_chat_generation(user, payload: dict, message_text: str) -> dict:
    thread = _resolve_thread_from_payload(user.id, payload)
    conversation = get_or_create_conversation_state(user.id, thread.id)
    if conversation.question_count >= current_app.config["CHAT_QUESTION_LIMIT"]:
        return {
            "limit_response": {
                "thread": thread.to_dict(),
                "messages": [_build_ephemeral_assistant_message(_question_limit_message())],
                "session": _session_payload(conversation),
            }
        }

    has_previous_assistant_message = (
        Message.query.filter_by(
            user_id=user.id,
            thread_id=thread.id,
            role="assistant",
        ).first()
        is not None
    )
    matched_app = _find_matched_app(message_text)
    surfaced_app = _maybe_surface_app_suggestion(conversation, message_text, matched_app)

    chat_memory = get_chat_memory(current_app)
    retrieval = None
    if chat_memory is not None:
        retrieval = chat_memory.retrieve_context(user.id, thread.id, message_text)

    return {
        "limit_response": None,
        "thread": thread,
        "conversation": conversation,
        "chat_memory": chat_memory,
        "surfaced_app": surfaced_app,
        "is_first_turn": not has_previous_assistant_message,
        "retrieved_background": [] if retrieval is None else retrieval.anchors,
        "recent_turns": [] if retrieval is None else retrieval.recent_turns,
        "prompt_log": None
        if retrieval is None
        else {
            "chroma_matches": retrieval.matches_returned,
            "threshold_matches": retrieval.matches_after_threshold,
            "budget_matches": retrieval.matches_after_budget,
            "background_chars": retrieval.background_chars,
            "fifo_turns": len(retrieval.recent_turns),
            "app_context": surfaced_app is not None,
        },
    }
