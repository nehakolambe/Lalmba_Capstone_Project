from flask import Blueprint

# Blueprints for modular route grouping. Keep prefixes flat to match requirements.
auth_bp = Blueprint("auth", __name__)
chat_bp = Blueprint("chat", __name__)
progress_bp = Blueprint("progress", __name__)
kb_bp = Blueprint("kb", __name__)
questionnaire_bp = Blueprint("questionnaire", __name__)

# Import route handlers to register them with the blueprints.
from . import auth, chat, kb, progress, questionnaire  # noqa: E402,F401
