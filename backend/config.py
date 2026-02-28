import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


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
    # Allow React dev server defaults (http://localhost:3000)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")
    OLLAMA_FALLBACK_ENABLED = os.getenv("OLLAMA_FALLBACK_ENABLED", "true")
    APPS_RAG_ENABLED = os.getenv("APPS_RAG_ENABLED", "true")


class TestConfig(Config):
    """Configuration tweaks for automated tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
