from __future__ import annotations


def _register_and_login(client, payload):
    client.post("/auth/register", json=payload)
    client.post("/auth/logout")
    client.post("/auth/login", json={"username": payload["username"], "pin": payload["pin"]})


def test_progress_requires_authentication(client):
    response = client.get("/progress")
    data = response.get_json()
    assert response.status_code == 401
    assert data["error"] == "Authentication required"


def test_progress_validation(client, registered_user_payload):
    _register_and_login(client, registered_user_payload)
    response = client.post("/progress", json={"milestone": "  "})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Milestone is required"


def test_progress_create_and_list(client, registered_user_payload):
    _register_and_login(client, registered_user_payload)

    create_response = client.post(
        "/progress",
        json={"milestone": "Completed lesson 1", "notes": "Strong participation"},
    )
    create_data = create_response.get_json()

    assert create_response.status_code == 201
    assert create_data["progress"]["milestone"] == "Completed lesson 1"

    list_response = client.get("/progress")
    list_data = list_response.get_json()

    assert list_response.status_code == 200
    assert len(list_data["progress"]) == 1
    assert list_data["progress"][0]["milestone"] == "Completed lesson 1"
