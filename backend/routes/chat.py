from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from flask import current_app, jsonify, request

from ..extensions import db
from ..models import Message
from ..rag.retriever import retrieve_chunks
from ..services.ollama_client import OllamaError, generate_response
from ..utils import login_required
from . import chat_bp

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an offline-first AI tutor running on a local Endless OS laptop. "
    "Answer using ONLY the provided app documentation context when possible. "
    "If the answer is not in the context, say you do not know and suggest checking the app or manual. "
    "Be concise, friendly, and practical. Use short steps when giving instructions."
)


def _build_prompt(user_text: str, sources: list[dict]) -> str:
    if not sources:
        return (
            f"{SYSTEM_PROMPT}\n\n"
            "Context: (none)\n\n"
            f"User question: {user_text}\n"
            "Answer:"
        )

    context_blocks = []
    for idx, source in enumerate(sources, start=1):
        context_blocks.append(f"[{idx}] {source['snippet']}")

    context_text = "\n".join(context_blocks)
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Context snippets:\n"
        f"{context_text}\n\n"
        "When relevant, cite snippets like [1], [2].\n\n"
        f"User question: {user_text}\n"
        "Answer:"
    )


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
    request_id = uuid4().hex[:8]
    started_at = perf_counter()
    payload = request.get_json(silent=True) or {}
    message_text = (payload.get("text") or "").strip()
    if not message_text:
        return jsonify({"error": "Message text is required"}), 400

    logger.info("chat_message start id=%s user_id=%s chars=%s", request_id, user.id, len(message_text))

    user_entry = Message(user_id=user.id, role="user", content=message_text)
    db.session.add(user_entry)
    db.session.flush()

    try:
        retrieved = retrieve_chunks(message_text, k=5)
    except Exception as exc:
        current_app.logger.warning("RAG retrieval failed: %s", exc)
        retrieved = []

    sources = [
        {
            "id": chunk.chunk_id,
            "app": chunk.metadata.get("app"),
            "source_path": chunk.metadata.get("source_path"),
            "snippet": chunk.snippet,
            "distance": chunk.distance,
        }
        for chunk in retrieved
    ]

    prompt = _build_prompt(message_text, sources)

    try:
        reply_text = generate_response(prompt)
    except OllamaError as exc:
        logger.warning(
            "chat_message ollama_error id=%s user_id=%s reason=%s",
            request_id,
            user.id,
            getattr(exc, "reason", str(exc)),
        )
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": "Local AI model is unavailable.",
                    "details": {"reason": getattr(exc, "reason", str(exc))},
                }
            ),
            503,
        )

    assistant_entry = Message(user_id=user.id, role="assistant", content=reply_text)
    db.session.add(assistant_entry)
    db.session.commit()
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "chat_message done id=%s user_id=%s sources=%s ms=%s",
        request_id,
        user.id,
        len(sources),
        elapsed_ms,
    )

    return (
        jsonify(
            {
                "messages": [user_entry.to_dict(), assistant_entry.to_dict()],
                "sources": sources,
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
