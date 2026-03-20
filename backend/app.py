from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import Config, _as_bool
from .db_schema import ensure_schema
from .extensions import db
from .routes import auth_bp, chat_bp, progress_bp
from .services.app_search import initialize_app_search
from .services.chat_memory import initialize_chat_memory

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def log_startup(app: Flask, host: str, port: int) -> None:
    logger = logging.getLogger("backend.startup")
    logger.info("Backend listening on http://%s:%s", host, port)
    logger.info("Registered routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = sorted(rule.methods - {"HEAD"})
        logger.info("  %s %s", ",".join(methods), rule.rule)


def create_app(config_class: type[Config] = Config) -> Flask:
    """Application factory for the chatbot backend."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    origins = [
        origin.strip()
        for origin in app.config.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    # TIP: Keep the list above in sync with the React dev origin to avoid mysterious "Failed to fetch" errors.
    CORS(
        app,
        resources={r"/*": {"origins": origins or ["http://localhost:3000"]}},
        supports_credentials=True,
        allow_headers=["Content-Type"],
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    )

    with app.app_context():
        db.create_all()
        ensure_schema()
    if app.config.get("APP_SEARCH_ENABLED", True):
        try:
            initialize_app_search(app)
        except Exception:
            logging.getLogger("backend.startup").exception(
                "App search failed to initialize; continuing without retrieval support"
            )
    initialize_chat_memory(app)


    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(progress_bp)

    @app.after_request
    def _apply_cors_hints(response):
        """Add explicit hints for browsers debugging tricky CORS preflights."""
        if request.method == "OPTIONS":
            response.headers.setdefault(
                "Access-Control-Allow-Methods",
                "GET,POST,PATCH,DELETE,OPTIONS",
            )
            response.headers.setdefault(
                "Access-Control-Allow-Headers",
                "Content-Type",
            )
        return response

    @app.get("/health")
    def health():
        """Basic readiness check for local development."""
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = _as_bool(os.getenv("FLASK_DEBUG"), False)
    app = create_app()
    log_startup(app, host, port)
    app.run(host=host, port=port, debug=debug)
