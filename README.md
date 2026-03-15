# Mama Akinyi Chatbot

Single reference for setting up and running this project on a new machine.
/home/lalmba/Documents/llama.cpp/build/bin/llama-server   -m /home/lalmba/.cache/llama.cpp/ggml-org_Meta-Llama-3.1-8B-Instruct-Q4_0-GGUF_meta-llama-3.1-8b-instruct-q4_0.gguf   -a local-model   -t 4   -ngl 6   --host 127.0.0.1   --port 8080

## Stack
- Backend: Flask + SQLAlchemy (`backend/`)
- Frontend: React (`matoso-chatbot/`)
- LLM runtime: `llama.cpp` server (required)

## Backend layout
- `backend/config.py`: app configuration and environment parsing
- `backend/extensions.py`: Flask extension instances
- `backend/models.py`: SQLAlchemy models
- `backend/db_schema.py`: schema/index compatibility helpers
- `backend/routes/`: auth/chat/progress route handlers
- `backend/utils.py`: auth/session and shared error helpers
- `backend/services/`: prompt + `llama.cpp` integration

## 1. Prerequisites
Install these first:
- Git
- Python 3.12+
- Node.js 18+ and npm
- `llama.cpp`
- A chat-capable `.gguf` model file

## 2. Clone
```bash
git clone <your-repo-url>
cd Lalmba_Capstone_Project
```

## 3. Start `llama.cpp` server (required)

This project expects the `llama-server` binary at:
- `/home/lalmba/Documents/llama.cpp/build/bin/llama-server`

You must also have a chat-capable `.gguf` model file somewhere on disk.

Set the model path:
```bash
export LLAMA_CPP_MODEL_PATH=/absolute/path/to/your-model.gguf
```

Optional runtime settings:
```bash
export LLAMA_CPP_SERVER_BIN=/home/lalmba/Documents/llama.cpp/build/bin/llama-server
export LLAMA_CPP_HOST=127.0.0.1
export LLAMA_CPP_PORT=8080
export LLAMA_CPP_MODEL_ALIAS=local-model
```

Start `llama-server` manually:
```bash
./scripts/start_llama_cpp.sh
```

Verify `llama-server` is reachable:
```bash
curl http://127.0.0.1:8080/v1/models
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
- `LLAMA_CPP_BASE_URL` (default `http://127.0.0.1:8080`)
- `LLAMA_CPP_MODEL_ALIAS` (default `local-model`)
- `LLAMA_CPP_MODEL_PATH` (required by `scripts/start_llama_cpp.sh`)
- `LLAMA_CPP_MAX_ATTEMPTS`
- `LLAMA_CPP_SERVER_BIN` (default `/home/lalmba/Documents/llama.cpp/build/bin/llama-server`)
- `LLAMA_CPP_HOST` (default `127.0.0.1`)
- `LLAMA_CPP_PORT` (default `8080`)
- `APP_MANIFEST_PATH` (default `backend/data/app_manifest.json`)
- `APP_EMBEDDING_MODEL` (default `all-MiniLM-L6-v2`)
- `APP_MATCH_THRESHOLD` (default `0.35`)
- `APP_SEARCH_ENABLED` (default `true`)

Frontend:
- `REACT_APP_API_BASE` (default `http://localhost:5000`)

## 7. Run the app
Terminal 1 (`llama.cpp`):
```bash
cd Lalmba_Capstone_Project
export LLAMA_CPP_MODEL_PATH=/absolute/path/to/your-model.gguf
./scripts/start_llama_cpp.sh
```

Terminal 2 (backend):
```bash
cd Lalmba_Capstone_Project
source .venv/bin/activate
python backend/server.py
```

Terminal 3 (frontend):
```bash
cd Lalmba_Capstone_Project/matoso-chatbot
npm start
```

URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`
- Backend health: `http://localhost:5000/health`
- `llama.cpp` models: `http://localhost:8080/v1/models`

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
  - confirm `llama-server` is running
  - confirm `LLAMA_CPP_MODEL_PATH` points to a valid `.gguf` file
  - confirm `curl http://127.0.0.1:8080/v1/models` returns your model alias
  - confirm backend `LLAMA_CPP_BASE_URL` matches the server port
- CORS errors in browser:
  - ensure frontend origin is present in `CORS_ORIGINS`
- `pytest: command not found`:
  - activate root `.venv`
  - install dependencies again with `pip install -r backend/requirements.txt`
