from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
