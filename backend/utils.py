from functools import wraps
from typing import Callable, Optional

from flask import jsonify, session

from .extensions import db
from .models import User


def get_current_user() -> Optional[User]:
    """Retrieve the logged-in user from the session, if any."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view: Callable):
    """Decorator that ensures a user is authenticated before proceeding."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error_response("Authentication required", 401)
        return view(user, *args, **kwargs)

    return wrapped


def error_response(message: str, status: int, *, details: Optional[dict] = None):
    """Return a backward-compatible error payload."""
    payload = {"message": message, "error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status
