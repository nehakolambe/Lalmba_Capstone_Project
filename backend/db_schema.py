from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db
from .models import ChatThread, Conversation, Message, Progress
from .services.chat_threads import LEGACY_CHAT_TITLE


def _ensure_column(table: str, column: str, column_type: str) -> None:
    inspector = inspect(db.engine)
    columns = {col["name"] for col in inspector.get_columns(table)}
    if column not in columns:
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))


def ensure_schema() -> None:
    """Ensure required tables, columns, and indexes exist."""
    inspector = inspect(db.engine)

    if not inspector.has_table("users"):
        db.create_all()
        return

    _ensure_column("users", "full_name", "TEXT")
    _ensure_column("users", "pin_hash", "TEXT")
    _ensure_column("users", "details", "TEXT")
    _ensure_column("users", "created_at", "DATETIME")

    if not inspector.has_table("messages"):
        Message.__table__.create(db.engine)
    else:
        _ensure_column("messages", "role", "TEXT")
        _ensure_column("messages", "content", "TEXT")
        _ensure_column("messages", "created_at", "DATETIME")
        _ensure_column("messages", "user_id", "INTEGER")
        _ensure_column("messages", "thread_id", "INTEGER")

    if inspector.has_table("messages"):
        indexes = {idx["name"] for idx in inspector.get_indexes("messages")}
        if "ix_messages_user_id" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_messages_user_id ON messages (user_id)")
            )
        if "ix_messages_created_at" not in indexes:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages (created_at)"
                )
            )
        if "ix_messages_thread_id" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_messages_thread_id ON messages (thread_id)")
            )

    if not inspector.has_table("chat_threads"):
        ChatThread.__table__.create(db.engine)
    else:
        _ensure_column("chat_threads", "user_id", "INTEGER")
        _ensure_column("chat_threads", "title", "TEXT")
        _ensure_column("chat_threads", "current_summary", "TEXT")
        _ensure_column("chat_threads", "turns_since_last_summary", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column("chat_threads", "created_at", "DATETIME")
        _ensure_column("chat_threads", "updated_at", "DATETIME")

    if inspector.has_table("chat_threads"):
        indexes = {idx["name"] for idx in inspector.get_indexes("chat_threads")}
        if "ix_chat_threads_user_id" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_chat_threads_user_id ON chat_threads (user_id)")
            )
        if "ix_chat_threads_updated_at" not in indexes:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_chat_threads_updated_at "
                    "ON chat_threads (updated_at)"
                )
            )

    if not inspector.has_table("conversations"):
        Conversation.__table__.create(db.engine)
    else:
        _ensure_column("conversations", "user_id", "INTEGER")
        _ensure_column("conversations", "current_summary", "TEXT")
        _ensure_column("conversations", "turns_since_last_summary", "INTEGER NOT NULL DEFAULT 0")

    if inspector.has_table("conversations"):
        indexes = {idx["name"] for idx in inspector.get_indexes("conversations")}
        if "ix_conversations_user_id" not in indexes:
            db.session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_conversations_user_id "
                    "ON conversations (user_id)"
                )
            )

    if inspector.has_table("progress"):
        _ensure_column("progress", "thread_id", "INTEGER")
        indexes = {idx["name"] for idx in inspector.get_indexes("progress")}
        if "ix_progress_thread_id" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_progress_thread_id ON progress (thread_id)")
            )

    _backfill_legacy_threads(inspector)

    db.session.commit()


def _backfill_legacy_threads(inspector) -> None:
    if not inspector.has_table("chat_threads"):
        return
    if not inspector.has_table("messages"):
        return

    user_ids: set[int] = set()

    if "thread_id" in {col["name"] for col in inspector.get_columns("messages")}:
        rows = db.session.execute(text("SELECT DISTINCT user_id FROM messages WHERE thread_id IS NULL"))
        user_ids.update(int(row[0]) for row in rows if row[0] is not None)

    if inspector.has_table("progress") and "thread_id" in {
        col["name"] for col in inspector.get_columns("progress")
    }:
        rows = db.session.execute(text("SELECT DISTINCT user_id FROM progress WHERE thread_id IS NULL"))
        user_ids.update(int(row[0]) for row in rows if row[0] is not None)

    if inspector.has_table("conversations"):
        rows = db.session.execute(text("SELECT DISTINCT user_id FROM conversations"))
        user_ids.update(int(row[0]) for row in rows if row[0] is not None)

    for user_id in sorted(user_ids):
        thread = (
            ChatThread.query.filter_by(user_id=user_id)
            .order_by(ChatThread.created_at.asc(), ChatThread.id.asc())
            .first()
        )
        legacy_state = Conversation.query.filter_by(user_id=user_id).first()

        if thread is None:
            thread = ChatThread(
                user_id=user_id,
                title=LEGACY_CHAT_TITLE,
                current_summary=getattr(legacy_state, "current_summary", None),
                turns_since_last_summary=getattr(legacy_state, "turns_since_last_summary", 0),
            )
            db.session.add(thread)
            db.session.flush()
        elif legacy_state is not None and not thread.current_summary:
            thread.current_summary = legacy_state.current_summary
            thread.turns_since_last_summary = legacy_state.turns_since_last_summary

        Message.query.filter_by(user_id=user_id, thread_id=None).update(
            {"thread_id": thread.id},
            synchronize_session=False,
        )

        if inspector.has_table("progress"):
            Progress.query.filter_by(user_id=user_id, thread_id=None).update(
                {"thread_id": thread.id},
                synchronize_session=False,
            )
