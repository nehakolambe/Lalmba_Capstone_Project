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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    messages = db.relationship(
        "Message", back_populates="user", cascade="all, delete-orphan"
    )
    progress_updates = db.relationship(
        "Progress", back_populates="user", cascade="all, delete-orphan"
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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }


class Message(db.Model):
    """Individual chat messages between a user and the assistant."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # "user" or "assistant"
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint("role IN ('user','assistant')", name="ck_messages_role"),
        db.Index("ix_messages_user_id", "user_id"),
        db.Index("ix_messages_created_at", "created_at"),
    )

    user = db.relationship("User", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class Progress(db.Model):
    """Milestones or learning progress entries recorded per user."""

    __tablename__ = "progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    milestone = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="progress_updates")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "milestone": self.milestone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
