from __future__ import annotations

from dataclasses import dataclass

from ..extensions import db
from ..models import Conversation, Message

SUMMARY_WINDOW_TURNS = 5
OVERLAP_TURNS = 1


@dataclass(frozen=True)
class CompletedTurn:
    user_text: str
    assistant_text: str


def get_or_create_conversation_state(user_id: int) -> Conversation:
    """Return the user's rolling conversation state, creating it if needed."""
    conversation = Conversation.query.filter_by(user_id=user_id).first()
    if conversation is None:
        conversation = Conversation(user_id=user_id, current_summary=None, turns_since_last_summary=0)
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
    overlap_turns: int = OVERLAP_TURNS,
    conversation: Conversation | None = None,
) -> tuple[list[CompletedTurn], list[CompletedTurn]]:
    """Return overlap turns from the summary boundary and all newer turns."""
    state = conversation or get_or_create_conversation_state(user_id)
    turns = _load_completed_turns(user_id)
    if not state.current_summary:
        return [], turns

    summary_window_end = max(0, len(turns) - max(0, state.turns_since_last_summary))
    summary_window_start = max(0, summary_window_end - SUMMARY_WINDOW_TURNS)
    overlap_start = max(summary_window_start, summary_window_end - max(0, overlap_turns))
    return turns[overlap_start:summary_window_end], turns[summary_window_end:]


def reset_conversation_state(user_id: int) -> None:
    """Delete the user's rolling conversation state for a clean reset."""
    Conversation.query.filter_by(user_id=user_id).delete()


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
            turns.append(
                CompletedTurn(
                    user_text=pending_user.content,
                    assistant_text=message.content,
                )
            )
            pending_user = None

    return turns
