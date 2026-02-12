from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db
from .models import AppDoc, AppEmbedding, Message, QuestionnaireResponse


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
    _ensure_column("users", "password_hash", "TEXT")
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

    if not inspector.has_table("questionnaire_responses"):
        QuestionnaireResponse.__table__.create(db.engine)
    else:
        _ensure_column("questionnaire_responses", "user_id", "INTEGER")
        _ensure_column("questionnaire_responses", "answers_json", "TEXT")
        _ensure_column("questionnaire_responses", "recommendation_text", "TEXT")
        _ensure_column("questionnaire_responses", "created_at", "DATETIME")

    if inspector.has_table("questionnaire_responses"):
        indexes = {idx["name"] for idx in inspector.get_indexes("questionnaire_responses")}
        if "ix_questionnaire_user_id" not in indexes:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_questionnaire_user_id "
                    "ON questionnaire_responses (user_id)"
                )
            )
        if "ix_questionnaire_created_at" not in indexes:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_questionnaire_created_at "
                    "ON questionnaire_responses (created_at)"
                )
            )

    if not inspector.has_table("app_docs"):
        AppDoc.__table__.create(db.engine)
    else:
        _ensure_column("app_docs", "app_name", "TEXT")
        _ensure_column("app_docs", "category", "TEXT")
        _ensure_column("app_docs", "requires_internet", "BOOLEAN")
        _ensure_column("app_docs", "cost", "TEXT")
        _ensure_column("app_docs", "swahili_support", "BOOLEAN")
        _ensure_column("app_docs", "keep_installed", "TEXT")
        _ensure_column("app_docs", "impact", "TEXT")
        _ensure_column("app_docs", "description", "TEXT")
        _ensure_column("app_docs", "source", "TEXT")
        _ensure_column("app_docs", "created_at", "DATETIME")

    if inspector.has_table("app_docs"):
        indexes = {idx["name"] for idx in inspector.get_indexes("app_docs")}
        if "ix_app_docs_app_name" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_app_docs_app_name ON app_docs (app_name)")
            )
        if "ix_app_docs_category" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_app_docs_category ON app_docs (category)")
            )
        if "ix_app_docs_impact" not in indexes:
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_app_docs_impact ON app_docs (impact)")
            )

    if not inspector.has_table("app_embeddings"):
        AppEmbedding.__table__.create(db.engine)
    else:
        _ensure_column("app_embeddings", "app_doc_id", "INTEGER")
        _ensure_column("app_embeddings", "embedding_json", "TEXT")
        _ensure_column("app_embeddings", "embedding_model", "TEXT")
        _ensure_column("app_embeddings", "created_at", "DATETIME")

    if inspector.has_table("app_embeddings"):
        indexes = {idx["name"] for idx in inspector.get_indexes("app_embeddings")}
        if "ix_app_embeddings_app_doc_id" not in indexes:
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_app_embeddings_app_doc_id "
                    "ON app_embeddings (app_doc_id)"
                )
            )

    db.session.commit()
