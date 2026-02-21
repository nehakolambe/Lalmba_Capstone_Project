from __future__ import annotations

import pytest

from backend import create_app
from backend.config import TestConfig
from backend.extensions import db


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    app.config.update(TESTING=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def registered_user_payload():
    return {
        "username": "testuser",
        "pin": "1234",
        "fullName": "Test User",
        "details": "sample",
    }
