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

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    log_startup(app, host, port)
    app.run(host=host, port=port, debug=True)
