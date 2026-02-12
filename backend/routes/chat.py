from __future__ import annotations

import json
import logging
import os
from time import perf_counter
from typing import Optional
from uuid import uuid4

from flask import current_app, jsonify, request

from ..extensions import db
from ..models import Message, QuestionnaireResponse
from ..rag.retriever import retrieve_chunks
from ..retrieval_apps import has_app_embeddings, retrieve_top_k_apps
from ..services.ollama_client import OllamaError, generate_response
from ..utils import login_required
from . import chat_bp

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an offline-first AI tutor running on a local Endless OS laptop. "
    "Use the provided context when answering. "
    "When app recommendations or app properties are requested, ONLY use the 'Relevant installed apps' list. "
    "Do not guess app capabilities. If the list lacks the needed info, ask a clarifying question. "
    "If the answer is not in context, say you do not know and suggest checking the app or manual. "
    "Be concise, friendly, and practical. Use short steps when giving instructions. "
    "Keep a warm, encouraging tone and use simple emojis when helpful."
)


def _normalize_bool(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unknown"


def _is_app_question(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "app",
        "apps",
        "application",
        "applications",
        "offline",
        "internet",
        "kiswahili",
        "swahili",
        "typing",
        "practice",
        "learn",
        "learning",
        "business",
        "course",
        "study",
        "software",
        "program",
    ]
    return any(keyword in lowered for keyword in keywords)


def _build_app_context(app_matches) -> str:
    lines = []
    for match in app_matches:
        app = match.app_doc
        offline = None if app.requires_internet is None else not app.requires_internet
        line = (
            f"- {app.app_name} | "
            f"Category: {app.category or 'Unknown'} | "
            f"Offline: {_normalize_bool(offline)} | "
            f"Swahili: {_normalize_bool(app.swahili_support)} | "
            f"Impact: {app.impact or 'Unknown'} | "
            f"Keep: {app.keep_installed or 'Unknown'} | "
            f"Summary: {(app.description or 'Not provided')[:200]}"
        )
        lines.append(line)
    return "\n".join(lines)


def _load_latest_questionnaire(user_id: int) -> dict:
    entry = (
        QuestionnaireResponse.query.filter_by(user_id=user_id)
        .order_by(QuestionnaireResponse.created_at.desc())
        .first()
    )
    if not entry or not entry.answers_json:
        return {}
    try:
        data = json.loads(entry.answers_json)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _format_profile_summary(answers: dict) -> str:
    def _stringify(value):
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item)
        return str(value) if value is not None else ""

    fields = [
        ("language", answers.get("language_preference")),
        ("literacy_level", answers.get("literacy_level")),
        ("typing_comfort", answers.get("typing_comfort")),
        ("learning_goals", answers.get("learning_goals")),
        ("topics", answers.get("topics_interest")),
        ("hours_per_week", answers.get("hours_per_week")),
    ]
    parts = []
    for key, value in fields:
        text = _stringify(value).strip()
        if text:
            parts.append(f"{key}={text}")
    return "; ".join(parts)


def _build_prompt(
    user_text: str,
    sources: list[dict],
    app_context: Optional[str],
    apps_db_ready: bool,
    app_question: bool,
    profile_summary: Optional[str],
) -> str:
    parts = [SYSTEM_PROMPT]

    if profile_summary:
        parts.append(f"User profile summary (from questionnaire): {profile_summary}")
        parts.append(
            "Personalize the answer based on the profile (reading level, typing comfort, goals). "
            "Keep instructions simple and supportive."
        )

    if app_context:
        parts.append("Relevant installed apps (from local apps list):")
        parts.append(app_context)
        parts.append(
            "Rule: When app recommendations or properties are requested, ONLY use the installed apps list above. "
            "If it does not contain enough info, ask a clarifying question."
        )
    elif app_question and not apps_db_ready:
        parts.append(
            "Apps database not loaded yet. Tell the user and suggest running the apps ingest script."
        )
    elif app_question and apps_db_ready:
        parts.append(
            "No relevant app entries were found for this question. Ask a clarifying question and avoid guessing."
        )

    if sources:
        context_blocks = []
        for idx, source in enumerate(sources, start=1):
            context_blocks.append(f"[{idx}] {source['snippet']}")
        context_text = "\n".join(context_blocks)
        parts.append("Context snippets:")
        parts.append(context_text)
        parts.append("When relevant, cite snippets like [1], [2].")
    else:
        parts.append("Context: (none)")

    parts.append(f"User question: {user_text}")
    parts.append("Answer:")
    return "\n\n".join(parts)


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

    app_question = _is_app_question(message_text)
    apps_rag_enabled = current_app.config.get("APPS_RAG_ENABLED", True)
    if isinstance(apps_rag_enabled, str):
        apps_rag_enabled = apps_rag_enabled.strip().lower() in {"1", "true", "yes", "y", "on"}

    app_matches = []
    apps_db_ready = False
    embed_model = current_app.config.get("OLLAMA_EMBED_MODEL") if apps_rag_enabled else None
    if apps_rag_enabled:
        try:
            apps_db_ready = has_app_embeddings(model=embed_model) if embed_model else has_app_embeddings()
            if app_question and apps_db_ready:
                if embed_model:
                    app_matches = retrieve_top_k_apps(
                        message_text, k=5, min_score=0.15, model=embed_model
                    )
                else:
                    app_matches = retrieve_top_k_apps(message_text, k=5, min_score=0.15)
        except Exception as exc:
            current_app.logger.warning("Apps RAG retrieval failed: %s", exc)
            app_matches = []

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

    app_context = _build_app_context(app_matches) if app_matches else None
    answers = _load_latest_questionnaire(user.id)
    profile_summary = _format_profile_summary(answers) if answers else ""
    prompt = _build_prompt(
        message_text,
        sources,
        app_context,
        apps_db_ready,
        app_question,
        profile_summary,
    )

    is_dev = os.getenv("FLASK_ENV", "").lower() == "development"
    if is_dev and profile_summary:
        logger.info(
            "[PROFILE_USED] user_id=%s summary=%s",
            user.id,
            profile_summary,
        )

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

    if app_question and not apps_db_ready:
        notice = "Apps database not loaded yet."
        if notice.lower() not in reply_text.lower():
            reply_text = f"{notice} {reply_text}".strip()

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

    response_payload = {
        "messages": [user_entry.to_dict(), assistant_entry.to_dict()],
        "sources": sources,
    }
    if is_dev:
        response_payload["debug_profile"] = profile_summary or ""

    return jsonify(response_payload), 201


@chat_bp.post("/chat/reset")
@login_required
def reset_chat(user):
    """Delete all messages for the authenticated user."""
    Message.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({"ok": True})


@chat_bp.get("/debug/apps/search")
@login_required
def debug_apps_search(user):
    """Lightweight endpoint to inspect app retrieval results."""
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"results": [], "count": 0})
    try:
        limit = int(request.args.get("k", 5))
    except ValueError:
        limit = 5
    limit = max(1, min(limit, 25))

    apps_rag_enabled = current_app.config.get("APPS_RAG_ENABLED", True)
    if isinstance(apps_rag_enabled, str):
        apps_rag_enabled = apps_rag_enabled.strip().lower() in {"1", "true", "yes", "y", "on"}
    if not apps_rag_enabled:
        return jsonify({"error": "Apps RAG is disabled"}), 400

    embed_model = current_app.config.get("OLLAMA_EMBED_MODEL")
    try:
        if embed_model:
            results = retrieve_top_k_apps(query, k=limit, model=embed_model)
        else:
            results = retrieve_top_k_apps(query, k=limit)
    except Exception as exc:
        current_app.logger.warning("Apps RAG debug failed: %s", exc)
        return jsonify({"error": "Apps retrieval failed"}), 500

    payload = []
    for match in results:
        app = match.app_doc
        payload.append(
            {
                "app_name": app.app_name,
                "category": app.category,
                "requires_internet": app.requires_internet,
                "swahili_support": app.swahili_support,
                "keep_installed": app.keep_installed,
                "impact": app.impact,
                "description": app.description,
                "score": match.score,
            }
        )

    return jsonify({"query": query, "count": len(payload), "results": payload})
