from __future__ import annotations


def test_register_success(client, registered_user_payload):
    response = client.post("/auth/register", json=registered_user_payload)
    data = response.get_json()

    assert response.status_code == 201
    assert data["user"]["username"] == registered_user_payload["username"]
    assert data["user"]["full_name"] == registered_user_payload["fullName"]
    assert data["user"]["profile_complete"] is False
    assert data["user"]["age_group"] is None


def test_register_validation_error(client):
    response = client.post("/auth/register", json={"username": "", "pin": "12"})
    data = response.get_json()

    assert response.status_code == 400
    assert data["message"] == "Invalid registration data"
    assert "error" in data
    assert "details" in data
    assert "fullName" in data["details"]


def test_register_duplicate_username(client, registered_user_payload):
    first = client.post("/auth/register", json=registered_user_payload)
    assert first.status_code == 201

    response = client.post("/auth/register", json=registered_user_payload)
    data = response.get_json()

    assert response.status_code == 409
    assert data["message"] == "Username is already taken."
    assert "username" in data["details"]


def test_login_success_and_session_lifecycle(client, registered_user_payload):
    client.post("/auth/register", json=registered_user_payload)
    client.post("/auth/logout")

    login_response = client.post(
        "/auth/login",
        json={"username": registered_user_payload["username"], "pin": registered_user_payload["pin"]},
    )
    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert login_data["user"]["username"] == registered_user_payload["username"]
    assert login_data["user"]["profile_complete"] is False

    current_response = client.get("/auth/me")
    current_data = current_response.get_json()
    assert current_response.status_code == 200
    assert current_data["user"]["username"] == registered_user_payload["username"]

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 200

    after_logout = client.get("/auth/me")
    after_logout_data = after_logout.get_json()
    assert after_logout_data["user"] is None


def test_login_failure(client):
    response = client.post("/auth/login", json={"username": "missing", "pin": "0000"})
    data = response.get_json()

    assert response.status_code == 401
    assert data["message"] == "Invalid username or PIN."
    assert data["error"] == "Invalid username or PIN."


def test_profile_update_and_fetch(client, registered_user_payload):
    client.post("/auth/register", json=registered_user_payload)

    response = client.patch(
        "/auth/profile",
        json={
            "age_group": "teen",
            "education_level": "class_9",
            "preferred_language": "english",
            "english_fluency": "can_do_some",
            "computer_literacy": "need_help",
        },
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["user"]["profile_complete"] is True
    assert data["user"]["education_level"] == "class_9"
    assert data["user"]["english_fluency"] == "can_do_some"
    assert data["user"]["computer_literacy"] == "need_help"

    profile_response = client.get("/auth/profile")
    profile_data = profile_response.get_json()
    assert profile_response.status_code == 200
    assert profile_data["profile"]["preferred_language"] == "english"


def test_profile_update_requires_english_fluency_for_english(client, registered_user_payload):
    client.post("/auth/register", json=registered_user_payload)

    response = client.patch(
        "/auth/profile",
        json={
            "age_group": "teen",
            "education_level": "class_9",
            "preferred_language": "english",
            "computer_literacy": "need_help",
        },
    )
    data = response.get_json()

    assert response.status_code == 400
    assert data["message"] == "Invalid profile data"
    assert "english_fluency" in data["details"]


def test_profile_update_clears_english_fluency_for_kiswahili(client, registered_user_payload):
    client.post("/auth/register", json=registered_user_payload)

    response = client.patch(
        "/auth/profile",
        json={
            "age_group": "adult",
            "education_level": "college",
            "preferred_language": "kiswahili",
            "english_fluency": "can_do_well",
            "computer_literacy": "can_do_well",
        },
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["user"]["preferred_language"] == "kiswahili"
    assert data["user"]["english_fluency"] is None


def test_profile_update_normalizes_legacy_skill_values(client, registered_user_payload):
    client.post("/auth/register", json=registered_user_payload)

    response = client.patch(
        "/auth/profile",
        json={
            "age_group": "teen",
            "education_level": "class_9",
            "preferred_language": "english",
            "english_fluency": "beginner",
            "computer_literacy": "advanced",
        },
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["user"]["english_fluency"] == "need_help"
    assert data["user"]["computer_literacy"] == "can_do_well"


def test_profile_fetch_normalizes_legacy_saved_values(client, app, registered_user_payload):
    client.post("/auth/register", json=registered_user_payload)

    with app.app_context():
        from backend.models import User

        user = User.query.filter_by(username=registered_user_payload["username"]).one()
        user.age_group = "adult"
        user.education_level = "adult"
        user.preferred_language = "english"
        user.english_fluency = "intermediate"
        user.computer_literacy = "beginner"
        from backend.extensions import db

        db.session.add(user)
        db.session.commit()

    response = client.get("/auth/profile")
    data = response.get_json()

    assert response.status_code == 200
    assert data["profile"]["english_fluency"] == "can_do_some"
    assert data["profile"]["computer_literacy"] == "need_help"
