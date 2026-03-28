from datetime import datetime

import bcrypt

from .extensions import db


class User(db.Model):
    """Application user with PIN authentication."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    age_group = db.Column(db.String(32), nullable=True)
    education_level = db.Column(db.String(32), nullable=True)
    preferred_language = db.Column(db.String(32), nullable=True)
    english_fluency = db.Column(db.String(32), nullable=True)
    computer_literacy = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    messages = db.relationship(
        "Message", back_populates="user", cascade="all, delete-orphan"
    )
    chat_threads = db.relationship(
        "ChatThread", back_populates="user", cascade="all, delete-orphan"
    )
    progress_updates = db.relationship(
        "Progress", back_populates="user", cascade="all, delete-orphan"
    )
    conversation = db.relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def set_pin(self, raw_pin: str) -> None:
        """Hash and store the provided PIN."""
        hashed = bcrypt.hashpw(raw_pin.encode("utf-8"), bcrypt.gensalt())
        self.pin_hash = hashed.decode("utf-8")

    def check_pin(self, raw_pin: str) -> bool:
        """Validate a raw PIN against the stored hash."""
        if not self.pin_hash:
            return False
        return bcrypt.checkpw(raw_pin.encode("utf-8"), self.pin_hash.encode("utf-8"))

    @property
    def profile_complete(self) -> bool:
        has_required_profile = all(
            (
                self.age_group,
                self.education_level,
                self.preferred_language,
                self.computer_literacy,
            )
        )
        if not has_required_profile:
            return False
        if self.preferred_language == "english":
            return bool(self.english_fluency)
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "details": self.details,
            "age_group": self.age_group,
            "education_level": self.education_level,
            "preferred_language": self.preferred_language,
            "english_fluency": self.english_fluency,
            "computer_literacy": self.computer_literacy,
            "profile_complete": self.profile_complete,
            "created_at": self.created_at.isoformat(),
        }


class Message(db.Model):
    """Individual chat messages between a user and the assistant."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    thread_id = db.Column(db.Integer, db.ForeignKey("chat_threads.id"), nullable=True)
    role = db.Column(db.String(32), nullable=False)  # "user" or "assistant"
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint("role IN ('user','assistant')", name="ck_messages_role"),
        db.Index("ix_messages_user_id", "user_id"),
        db.Index("ix_messages_thread_id", "thread_id"),
        db.Index("ix_messages_created_at", "created_at"),
    )

    user = db.relationship("User", back_populates="messages")
    thread = db.relationship("ChatThread", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class ChatThread(db.Model):
    """A user-owned chat thread with its own rolling memory state."""

    __tablename__ = "chat_threads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="New chat")
    current_summary = db.Column(db.Text, nullable=True)
    turns_since_last_summary = db.Column(db.Integer, nullable=False, default=0)
    question_count = db.Column(db.Integer, nullable=False, default=0)
    pending_app_choice = db.Column(db.Boolean, nullable=False, default=False)
    pending_app_id = db.Column(db.String(255), nullable=True)
    pending_app_question = db.Column(db.Text, nullable=True)
    last_suggested_app_id = db.Column(db.String(255), nullable=True)
    last_app_topic_hint = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        db.Index("ix_chat_threads_user_id", "user_id"),
        db.Index("ix_chat_threads_updated_at", "updated_at"),
    )

    user = db.relationship("User", back_populates="chat_threads")
    messages = db.relationship(
        "Message", back_populates="thread", cascade="all, delete-orphan"
    )
    progress_entries = db.relationship(
        "Progress", back_populates="thread", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "current_summary": self.current_summary,
            "turns_since_last_summary": self.turns_since_last_summary,
            "question_count": self.question_count,
            "pending_app_choice": self.pending_app_choice,
            "pending_app_id": self.pending_app_id,
            "pending_app_question": self.pending_app_question,
            "last_suggested_app_id": self.last_suggested_app_id,
            "last_app_topic_hint": self.last_app_topic_hint,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Conversation(db.Model):
    """Per-user chat state for rolling summaries and turn counts."""

    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    current_summary = db.Column(db.Text, nullable=True)
    turns_since_last_summary = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.Index("ix_conversations_user_id", "user_id", unique=True),)

    user = db.relationship("User", back_populates="conversation")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "current_summary": self.current_summary,
            "turns_since_last_summary": self.turns_since_last_summary,
        }


class Progress(db.Model):
    """Milestones or learning progress entries recorded per user."""

    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    thread_id = db.Column(db.Integer, db.ForeignKey("chat_threads.id"), nullable=True)
    milestone = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="progress_updates")
    thread = db.relationship("ChatThread", back_populates="progress_entries")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "milestone": self.milestone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
