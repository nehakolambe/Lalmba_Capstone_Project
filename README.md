# Mama Akinyi Chatbot

Single reference for setting up and running this project on a new machine.

## Stack
- Backend: Flask + SQLAlchemy (`backend/`)
- Frontend: React (`matoso-chatbot/`)
- LLM runtime: Ollama (required)

## Backend layout
- `backend/config.py`: app configuration and environment parsing
- `backend/extensions.py`: Flask extension instances
- `backend/models.py`: SQLAlchemy models
- `backend/db_schema.py`: schema/index compatibility helpers
- `backend/routes/`: auth/chat/progress route handlers
- `backend/utils.py`: auth/session and shared error helpers
- `backend/services/`: prompt + Ollama integration

## 1. Prerequisites
Install these first:
- Git
- Python 3.12+
- Node.js 18+ and npm
- Ollama

## 2. Clone
```bash
git clone <your-repo-url>
cd Lalmba_Capstone_Project
```

## 3. Install and start Ollama (required)

Install Ollama:
- Linux/macOS: use official installer from `https://ollama.com/download`
- Windows: install Ollama Desktop from the same page

Start Ollama manually (works on all machines):
```bash
ollama serve
```

If your machine uses a service manager and Ollama is installed as a service:
```bash
# Linux (systemd)
sudo systemctl start ollama
sudo systemctl enable ollama
```

Pull the model used by this app (default):
```bash
ollama pull llama3.2:3b
```

Verify Ollama is reachable:
```bash
curl http://127.0.0.1:11434/api/tags
```

## 4. Python environment (single root `.venv`)

Create and activate the only supported venv location:
```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

Phase 1 app search is part of backend startup. Those dependencies now include a
local sentence-embedding runtime for the `all-MiniLM-L6-v2` app index.

## 5. Frontend dependencies
```bash
cd matoso-chatbot
npm install
cd ..
```

## 6. Environment variables
Defaults work for local dev, but these can be set if needed.

Backend:
- `FLASK_SECRET_KEY`
- `DATABASE_URL` (default local SQLite)
- `CORS_ORIGINS` (default includes `http://localhost:3000`)
- `FLASK_DEBUG` (`true` or `false`)
- `LOG_LEVEL`
- `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`)
- `OLLAMA_MODEL` (default `llama3.2:3b`)
- `OLLAMA_MAX_ATTEMPTS`
- `APP_MANIFEST_PATH` (default `backend/data/app_manifest.json`)
- `APP_EMBEDDING_MODEL` (default `all-MiniLM-L6-v2`)
- `APP_MATCH_THRESHOLD` (default `0.35`)
- `APP_SEARCH_ENABLED` (default `true`)

Frontend:
- `REACT_APP_API_BASE` (default `http://localhost:5000`)

## 7. Run the app
Terminal 1 (backend):
```bash
cd Lalmba_Capstone_Project
source .venv/bin/activate
python backend/server.py
```

Terminal 2 (frontend):
```bash
cd Lalmba_Capstone_Project/matoso-chatbot
npm start
```

URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`
- Backend health: `http://localhost:5000/health`

## 8. API reference
Auth:
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /auth/session` (alias)

Chat:
- `POST /chat/message`
- `GET /chat/history`
- `POST /chat/reset`

Progress:
- `GET /progress`
- `POST /progress`

## Local app manifest
The backend now loads local app metadata from:
- `backend/data/app_manifest.json`

Each manifest entry must include:
- `app_id`
- `name`
- `description`
- `tutorial_steps`

On server startup, the backend validates this file and builds an in-memory
vector index from each app description.

## 9. Test commands
Frontend tests:
```bash
cd Lalmba_Capstone_Project/matoso-chatbot
CI=true npm test -- --watchAll=false
```

Backend tests (after `pytest` is installed in `.venv`):
```bash
cd Lalmba_Capstone_Project
source .venv/bin/activate
pytest backend/tests -q
```

## 10. Troubleshooting
- `Cannot connect to server` in frontend:
  - confirm backend is running on `:5000`
  - confirm `REACT_APP_API_BASE` if non-default
- Backend starts but replies fail:
  - confirm `ollama serve` is running
  - confirm model exists: `ollama list`
  - confirm selected `OLLAMA_MODEL` is installed
- CORS errors in browser:
  - ensure frontend origin is present in `CORS_ORIGINS`
- `pytest: command not found`:
  - activate root `.venv`
  - install dependencies again with `pip install -r backend/requirements.txt`
