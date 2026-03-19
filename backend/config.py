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
    APP_MANIFEST_PATH = os.getenv(
        "APP_MANIFEST_PATH",
        str(BASE_DIR / "data" / "app_manifest.json"),
    )
    APP_EMBEDDING_MODEL = os.getenv("APP_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    try:
        APP_MATCH_THRESHOLD = float(os.getenv("APP_MATCH_THRESHOLD", "0.35"))
    except ValueError:
        APP_MATCH_THRESHOLD = 0.35
    APP_SEARCH_ENABLED = _as_bool(os.getenv("APP_SEARCH_ENABLED"), True)
    CHAT_MEMORY_ENABLED = _as_bool(os.getenv("CHAT_MEMORY_ENABLED"), True)
    CHAT_MEMORY_EMBEDDING_MODEL = os.getenv("CHAT_MEMORY_EMBEDDING_MODEL", "").strip()
    CHAT_MEMORY_PERSIST_DIR = os.getenv(
        "CHAT_MEMORY_PERSIST_DIR",
        str(BASE_DIR / "data" / "chat_memory_chroma"),
    )
    CHAT_MEMORY_COLLECTION_NAME = os.getenv("CHAT_MEMORY_COLLECTION_NAME", "chat_memory")
    try:
        CHAT_MEMORY_TOP_K = max(1, int(os.getenv("CHAT_MEMORY_TOP_K", "5")))
    except ValueError:
        CHAT_MEMORY_TOP_K = 5
    try:
        CHAT_MEMORY_SCORE_THRESHOLD = float(os.getenv("CHAT_MEMORY_SCORE_THRESHOLD", "0.35"))
    except ValueError:
        CHAT_MEMORY_SCORE_THRESHOLD = 0.35
    try:
        CHAT_MEMORY_ANCHOR_CHAR_BUDGET = max(
            0,
            int(os.getenv("CHAT_MEMORY_ANCHOR_CHAR_BUDGET", "1200")),
        )
    except ValueError:
        CHAT_MEMORY_ANCHOR_CHAR_BUDGET = 1200
    try:
        CHAT_MEMORY_FIFO_TURNS = max(1, int(os.getenv("CHAT_MEMORY_FIFO_TURNS", "3")))
    except ValueError:
        CHAT_MEMORY_FIFO_TURNS = 3
    try:
        CHAT_QUESTION_LIMIT = max(1, int(os.getenv("CHAT_QUESTION_LIMIT", "10")))
    except ValueError:
        CHAT_QUESTION_LIMIT = 10
    try:
        CHAT_SUMMARY_WINDOW_TURNS = max(1, int(os.getenv("CHAT_SUMMARY_WINDOW_TURNS", "5")))
    except ValueError:
        CHAT_SUMMARY_WINDOW_TURNS = 5
    try:
        CHAT_SUMMARY_OVERLAP_TURNS = max(0, int(os.getenv("CHAT_SUMMARY_OVERLAP_TURNS", "1")))
    except ValueError:
        CHAT_SUMMARY_OVERLAP_TURNS = 1
    LOG_FULL_PROMPTS = _as_bool(os.getenv("LOG_FULL_PROMPTS"), False)


class TestConfig(Config):
    """Configuration tweaks for automated tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    APP_SEARCH_ENABLED = False
    CHAT_MEMORY_ENABLED = False
