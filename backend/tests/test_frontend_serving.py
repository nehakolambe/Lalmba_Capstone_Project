from __future__ import annotations

from pathlib import Path

from backend import create_app
from backend.config import TestConfig
from backend.extensions import db


def test_root_returns_helpful_error_when_frontend_build_missing(tmp_path: Path):
    class MissingBuildConfig(TestConfig):
        FRONTEND_BUILD_DIR = str(tmp_path / "missing-build")

    app = create_app(MissingBuildConfig)
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    response = client.get("/")
    data = response.get_json()

    assert response.status_code == 503
    assert data["error"] == "Frontend build not found"
    assert "build_dir" in data["details"]


def test_root_serves_built_frontend_index(tmp_path: Path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "index.html").write_text("<html><body>offline ui</body></html>", encoding="utf-8")

    class BuiltFrontendConfig(TestConfig):
        FRONTEND_BUILD_DIR = str(build_dir)

    app = create_app(BuiltFrontendConfig)
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"offline ui" in response.data
