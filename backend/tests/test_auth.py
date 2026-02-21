from __future__ import annotations


def test_register_success(client, registered_user_payload):
    response = client.post("/auth/register", json=registered_user_payload)
    data = response.get_json()

    assert response.status_code == 201
    assert data["user"]["username"] == registered_user_payload["username"]
    assert data["user"]["full_name"] == registered_user_payload["fullName"]


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
