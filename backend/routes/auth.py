from __future__ import annotations

from typing import Tuple

from flask import jsonify, request, session

from ..extensions import db
from ..models import User
from ..utils import error_response, get_current_user, login_required
from . import auth_bp

AGE_GROUP_OPTIONS = frozenset({"child", "teen", "adult"})
EDUCATION_LEVEL_OPTIONS = frozenset(
    {
        "class_1",
        "class_2",
        "class_3",
        "class_4",
        "class_5",
        "class_6",
        "class_7",
        "class_8",
        "class_9",
        "class_10",
        "high_school",
        "college",
        "adult",
    }
)
LANGUAGE_OPTIONS = frozenset({"english", "kiswahili"})
FLUENCY_OPTIONS = frozenset({"beginner", "intermediate", "advanced"})
COMPUTER_LITERACY_OPTIONS = frozenset({"beginner", "intermediate", "advanced"})


def _validate_credentials(data) -> Tuple[str, str]:
    username = (data.get("username") or "").strip()
    pin = (data.get("pin") or "").strip()

    if not username or not pin:
        raise ValueError("Username and PIN are required")
    return username, pin


def _normalize_choice(value: object) -> str:
    return str(value or "").strip().lower()


def _validate_choice(
    value: object,
    *,
    field: str,
    label: str,
    valid_options: frozenset[str],
    errors: dict[str, str],
) -> str | None:
    normalized = _normalize_choice(value)
    if not normalized:
        errors[field] = f"{label} is required."
        return None
    if normalized not in valid_options:
        errors[field] = f"Invalid {label.lower()}."
        return None
    return normalized


def _validate_profile_payload(payload: dict) -> tuple[dict[str, str | None] | None, dict[str, str]]:
    errors: dict[str, str] = {}
    age_group = _validate_choice(
        payload.get("age_group") or payload.get("ageGroup"),
        field="age_group",
        label="Age group",
        valid_options=AGE_GROUP_OPTIONS,
        errors=errors,
    )
    education_level = _validate_choice(
        payload.get("education_level") or payload.get("educationLevel"),
        field="education_level",
        label="Education level",
        valid_options=EDUCATION_LEVEL_OPTIONS,
        errors=errors,
    )
    preferred_language = _validate_choice(
        payload.get("preferred_language") or payload.get("preferredLanguage"),
        field="preferred_language",
        label="Preferred language",
        valid_options=LANGUAGE_OPTIONS,
        errors=errors,
    )
    computer_literacy = _validate_choice(
        payload.get("computer_literacy") or payload.get("computerLiteracy"),
        field="computer_literacy",
        label="Computer literacy",
        valid_options=COMPUTER_LITERACY_OPTIONS,
        errors=errors,
    )

    english_fluency: str | None = None
    raw_english_fluency = payload.get("english_fluency") or payload.get("englishFluency")
    if preferred_language == "english":
        english_fluency = _validate_choice(
            raw_english_fluency,
            field="english_fluency",
            label="English fluency",
            valid_options=FLUENCY_OPTIONS,
            errors=errors,
        )
    else:
        normalized = _normalize_choice(raw_english_fluency)
        if normalized and normalized not in FLUENCY_OPTIONS:
            errors["english_fluency"] = "Invalid english fluency."

    if errors:
        return None, errors

    return (
        {
            "age_group": age_group,
            "education_level": education_level,
            "preferred_language": preferred_language,
            "english_fluency": english_fluency if preferred_language == "english" else None,
            "computer_literacy": computer_literacy,
        },
        {},
    )


def _apply_profile_data(user: User, profile_data: dict[str, str | None]) -> None:
    user.age_group = profile_data["age_group"]
    user.education_level = profile_data["education_level"]
    user.preferred_language = profile_data["preferred_language"]
    user.english_fluency = profile_data["english_fluency"]
    user.computer_literacy = profile_data["computer_literacy"]


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
        return error_response(str(exc), 401)

    user = User.query.filter_by(username=username).one_or_none()
    if not user or not user.check_pin(pin):
        return error_response("Invalid username or PIN.", 401)

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


@auth_bp.get("/auth/profile")
@login_required
def get_profile(user):
    """Return the current user's questionnaire profile."""
    return jsonify({"user": user.to_dict(), "profile": user.to_dict()})


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
        return error_response("Invalid registration data", 400, details=errors)

    existing = User.query.filter_by(username=username).one_or_none()
    if existing:
        return error_response(
            "Username is already taken.",
            409,
            details={"username": "Please choose a different username."},
        )

    user = User(username=username, full_name=full_name, details=details or None)
    user.set_pin(pin)
    db.session.add(user)
    db.session.flush()

    session["user_id"] = user.id
    session.permanent = bool(payload.get("remember"))

    db.session.commit()

    return jsonify({"user": user.to_dict()}), 201


@auth_bp.patch("/auth/profile")
@login_required
def update_profile(user):
    """Create or update the logged-in user's questionnaire profile."""
    payload = request.get_json(silent=True) or {}
    profile_data, errors = _validate_profile_payload(payload)
    if errors:
        return error_response("Invalid profile data", 400, details=errors)

    _apply_profile_data(user, profile_data or {})
    db.session.add(user)
    db.session.commit()
    return jsonify({"user": user.to_dict(), "profile": user.to_dict()})
