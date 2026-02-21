"""Development entrypoint for the Mama Akinyi chatbot backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the package is importable when running `python backend/server.py` directly.
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import create_app
from backend.app import log_startup
from backend.config import _as_bool

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = _as_bool(os.getenv("FLASK_DEBUG"), False)
    log_startup(app, host, port)
    app.run(host=host, port=port, debug=debug)
