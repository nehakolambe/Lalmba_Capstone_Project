from __future__ import annotations

from dataclasses import dataclass

from flask import current_app, has_app_context

from ..extensions import db
from ..models import Conversation, Message

DEFAULT_SUMMARY_WINDOW_TURNS = 5
DEFAULT_OVERLAP_TURNS = 1
DEFAULT_QUESTION_LIMIT = 10


@dataclass(frozen=True)
class CompletedTurn:
    user_text: str
    assistant_text: str


def get_or_create_conversation_state(user_id: int) -> Conversation:
    """Return the user's rolling conversation state, creating it if needed."""
    conversation = Conversation.query.filter_by(user_id=user_id).first()
    if conversation is None:
        conversation = Conversation(
            user_id=user_id,
            current_summary=None,
            turns_since_last_summary=0,
            question_count=0,
            pending_app_choice=False,
            pending_app_id=None,
            pending_app_question=None,
            last_suggested_app_id=None,
            last_app_topic_hint=None,
        )
        db.session.add(conversation)
        db.session.flush()
    return conversation


def load_recent_completed_turns(user_id: int, limit: int) -> list[CompletedTurn]:
    """Return the most recent fully completed user-assistant turns."""
    if limit <= 0:
        return []
    turns = _load_completed_turns(user_id)
    return turns[-limit:]


def load_turns_since_last_summary(
    user_id: int,
    *,
    overlap_turns: int = DEFAULT_OVERLAP_TURNS,
    conversation: Conversation | None = None,
) -> tuple[list[CompletedTurn], list[CompletedTurn]]:
    """Return overlap turns from the summary boundary and all newer turns."""
    state = conversation or get_or_create_conversation_state(user_id)
    turns = _load_completed_turns(user_id)
    if not state.current_summary:
        return [], turns

    summary_window_turns = _summary_window_turns()
    summary_window_end = max(0, len(turns) - max(0, state.turns_since_last_summary))
    summary_window_start = max(0, summary_window_end - summary_window_turns)
    overlap_start = max(summary_window_start, summary_window_end - max(0, overlap_turns))
    return turns[overlap_start:summary_window_end], turns[summary_window_end:]


def reset_conversation_state(user_id: int) -> None:
    """Delete the user's rolling conversation state for a clean reset."""
    Conversation.query.filter_by(user_id=user_id).delete()


def clear_pending_app_choice(conversation: Conversation) -> None:
    conversation.pending_app_choice = False
    conversation.pending_app_id = None
    conversation.pending_app_question = None


def set_pending_app_choice(
    conversation: Conversation,
    *,
    app_id: str,
    question_text: str,
) -> None:
    conversation.pending_app_choice = True
    conversation.pending_app_id = app_id
    conversation.pending_app_question = question_text


def build_session_metadata(conversation: Conversation) -> dict[str, int | bool | str | None]:
    question_limit = _question_limit()
    questions_used = max(0, conversation.question_count)
    questions_remaining = max(0, question_limit - questions_used)
    return {
        "question_count": questions_used,
        "question_limit": question_limit,
        "questions_remaining": questions_remaining,
        "limit_reached": questions_remaining == 0,
    }


def should_refresh_summary(conversation: Conversation) -> bool:
    return max(0, conversation.turns_since_last_summary) >= _summary_window_turns()


def _summary_window_turns() -> int:
    if not has_app_context():
        return DEFAULT_SUMMARY_WINDOW_TURNS
    return max(
        1,
        int(current_app.config.get("CHAT_SUMMARY_WINDOW_TURNS", DEFAULT_SUMMARY_WINDOW_TURNS)),
    )


def summary_overlap_turns() -> int:
    if not has_app_context():
        return DEFAULT_OVERLAP_TURNS
    return max(
        0,
        int(current_app.config.get("CHAT_SUMMARY_OVERLAP_TURNS", DEFAULT_OVERLAP_TURNS)),
    )


def _question_limit() -> int:
    if not has_app_context():
        return DEFAULT_QUESTION_LIMIT
    return max(1, int(current_app.config.get("CHAT_QUESTION_LIMIT", DEFAULT_QUESTION_LIMIT)))


def _load_completed_turns(user_id: int) -> list[CompletedTurn]:
    messages = (
        Message.query.filter_by(user_id=user_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    turns: list[CompletedTurn] = []
    pending_user: Message | None = None

    for message in messages:
        if message.role == "user":
            pending_user = message
            continue
        if message.role == "assistant" and pending_user is not None:
            turn = CompletedTurn(
                user_text=pending_user.content,
                assistant_text=message.content,
            )
            if not _is_control_turn(turn):
                turns.append(turn)
            pending_user = None

    return turns


def _is_control_turn(turn: CompletedTurn) -> bool:
    normalized_user = " ".join((turn.user_text or "").strip().lower().split())
    normalized_assistant = " ".join((turn.assistant_text or "").strip().lower().split())
    if normalized_user in {
        "app",
        "here",
        "use app",
        "the app",
        "learn in app",
        "through app",
        "chat",
        "learn here",
        "teach me here",
        "in chat",
    }:
        return True
    if "reply `app` to learn using the app" in normalized_assistant:
        return True
    if normalized_assistant.startswith("please reply with `app`"):
        return True
    return False
