from __future__ import annotations

from dataclasses import dataclass

from ..extensions import db
from ..models import ChatThread, Conversation, Message

SUMMARY_WINDOW_TURNS = 5
OVERLAP_TURNS = 1


@dataclass(frozen=True)
class CompletedTurn:
    user_text: str
    assistant_text: str


def get_or_create_conversation_state(user_id: int, thread_id: int | None = None) -> ChatThread:
    """Return the thread's rolling conversation state, creating a thread if needed."""
    thread = None
    if thread_id is not None:
        thread = ChatThread.query.filter_by(id=thread_id, user_id=user_id).first()
    if thread is None:
        thread = (
            ChatThread.query.filter_by(user_id=user_id)
            .order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
            .first()
        )
    if thread is None:
        thread = ChatThread(user_id=user_id, title="New chat")
        db.session.add(thread)
        db.session.flush()
    return thread


def load_recent_completed_turns(
    user_id: int,
    thread_id: int,
    limit: int,
) -> list[CompletedTurn]:
    """Return the most recent fully completed user-assistant turns."""
    if limit <= 0:
        return []
    turns = _load_completed_turns(user_id, thread_id)
    return turns[-limit:]


def load_turns_since_last_summary(
    user_id: int,
    thread_id: int,
    *,
    overlap_turns: int = OVERLAP_TURNS,
    conversation: ChatThread | None = None,
) -> tuple[list[CompletedTurn], list[CompletedTurn]]:
    """Return overlap turns from the summary boundary and all newer turns."""
    state = conversation or get_or_create_conversation_state(user_id, thread_id)
    turns = _load_completed_turns(user_id, thread_id)
    if not state.current_summary:
        return [], turns

    summary_window_end = max(0, len(turns) - max(0, state.turns_since_last_summary))
    summary_window_start = max(0, summary_window_end - SUMMARY_WINDOW_TURNS)
    overlap_start = max(summary_window_start, summary_window_end - max(0, overlap_turns))
    return turns[overlap_start:summary_window_end], turns[summary_window_end:]


def reset_conversation_state(user_id: int, thread_id: int | None = None) -> None:
    """Clear the thread's rolling summary state and remove legacy single-thread state."""
    thread = get_or_create_conversation_state(user_id, thread_id)
    thread.current_summary = None
    thread.turns_since_last_summary = 0
    Conversation.query.filter_by(user_id=user_id).delete()


def _load_completed_turns(user_id: int, thread_id: int) -> list[CompletedTurn]:
    messages = (
        Message.query.filter_by(user_id=user_id, thread_id=thread_id)
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
