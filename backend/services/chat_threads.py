from __future__ import annotations

from datetime import datetime

from ..extensions import db
from ..models import ChatThread

DEFAULT_CHAT_TITLE = "New chat"
LEGACY_CHAT_TITLE = "Previous chat"


def normalize_thread_title(raw_title: str | None) -> str:
    cleaned = (raw_title or "").strip()
    return cleaned[:255] or DEFAULT_CHAT_TITLE


def build_auto_thread_title(message_text: str, *, fallback: str = DEFAULT_CHAT_TITLE) -> str:
    cleaned = " ".join((message_text or "").strip().split())
    if not cleaned:
        return fallback
    if len(cleaned) <= 60:
        return cleaned
    return f"{cleaned[:57].rstrip()}..."


def list_threads(user_id: int) -> list[ChatThread]:
    return (
        ChatThread.query.filter_by(user_id=user_id)
        .order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
        .all()
    )


def create_thread(user_id: int, *, title: str | None = None) -> ChatThread:
    thread = ChatThread(user_id=user_id, title=normalize_thread_title(title))
    db.session.add(thread)
    db.session.flush()
    return thread


def get_thread(user_id: int, thread_id: int | None) -> ChatThread | None:
    if thread_id is None:
        return None
    return ChatThread.query.filter_by(id=thread_id, user_id=user_id).first()


def get_or_create_default_thread(user_id: int) -> ChatThread:
    thread = (
        ChatThread.query.filter_by(user_id=user_id)
        .order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
        .first()
    )
    if thread is None:
        thread = create_thread(user_id)
    return thread


def touch_thread(thread: ChatThread) -> None:
    thread.updated_at = datetime.utcnow()
