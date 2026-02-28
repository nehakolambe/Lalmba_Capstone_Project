from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db
from .models import Conversation, Message


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

    db.session.commit()
