import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Flask configuration with sensible defaults for local development."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'lalmba_chat.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False  # Preserve key order in JSON responses
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), False)
    # Allow React dev server defaults (http://localhost:3000)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")


class TestConfig(Config):
    """Configuration tweaks for automated tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
