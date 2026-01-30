from __future__ import annotations

from typing import Tuple

from flask import jsonify, request, session

from ..extensions import db
from ..models import User
from ..utils import get_current_user, login_required
from . import auth_bp


def _validate_credentials(data) -> Tuple[str, str]:
    username = (data.get("username") or "").strip()
    pin = (data.get("pin") or "").strip()

    if not username or not pin:
        raise ValueError("Username and PIN are required")
    return username, pin


@auth_bp.route("/auth/login", methods=["OPTIONS"])
def login_options():
    """Handle CORS preflight checks for the login endpoint."""
    return ("", 204)


@auth_bp.post("/auth/login")
def login():
    """Authenticate an existing user."""
    payload = request.get_json(silent=True) or {}

    try:
        username, pin = _validate_credentials(payload)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 401

    user = User.query.filter_by(username=username).one_or_none()
    if not user or not user.check_pin(pin):
        return jsonify({"message": "Invalid username or PIN."}), 401

    db.session.add(user)  # ensure attached in case of expired session
    session["user_id"] = user.id
    session.permanent = bool(payload.get("remember"))

    db.session.commit()

    return jsonify({"user": user.to_dict()})


@auth_bp.post("/auth/logout")
@login_required
def logout(user):
    """Clear the session for the logged-in user."""
    session.clear()
    return jsonify({"ok": True})


@auth_bp.get("/auth/me")
def current_user():
    """Return the currently authenticated user, if any."""
    user = get_current_user()
    if not user:
        return jsonify({"user": None}), 200
    return jsonify({"user": user.to_dict()})


@auth_bp.get("/auth/session")
def current_session():
    """Backward-compatible alias for /auth/me."""
    return current_user()


@auth_bp.route("/auth/register", methods=["OPTIONS"])
def register_options():
    """Handle CORS preflight checks for the register endpoint."""
    return ("", 204)


@auth_bp.post("/auth/register")
def register():
    """Create a new user account with optional profile metadata."""
    payload = request.get_json(silent=True) or {}

    errors: dict[str, str] = {}
    username = (payload.get("username") or "").strip()
    pin = (payload.get("pin") or "").strip()
    full_name = (payload.get("fullName") or payload.get("full_name") or "").strip()
    details = (payload.get("details") or "").strip()

    if not username:
        errors["username"] = "Username is required."
    if not pin:
        errors["pin"] = "PIN is required."
    elif len(pin) < 4:
        errors["pin"] = "PIN must be at least 4 characters."
    if not full_name:
        errors["fullName"] = "Full name is required."

    if errors:
        return jsonify({"message": "Invalid registration data", "details": errors}), 400

    existing = User.query.filter_by(username=username).one_or_none()
    if existing:
        return (
            jsonify(
                {
                    "message": "Username is already taken.",
                    "details": {"username": "Please choose a different username."},
                }
            ),
            409,
        )

    user = User(username=username, full_name=full_name, details=details or None)
    user.set_pin(pin)
    db.session.add(user)
    db.session.flush()

    session["user_id"] = user.id
    session.permanent = bool(payload.get("remember"))

    db.session.commit()

    return jsonify({"user": user.to_dict()}), 201
