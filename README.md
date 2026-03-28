# Mama Akinyi Chatbot

Mama Akinyi Chatbot is a local-first learning assistant with a Flask backend, a React frontend, and a `llama.cpp`-served language model. It supports user login, chat history, progress tracking, app recommendations, and multi-turn tutoring memory so the assistant can keep context across a lesson.

This README is a setup guide for getting the project running on a new laptop. It covers installing dependencies, building `llama.cpp`, serving the local `gpt-oss-20b` model, starting the backend and frontend, and understanding the current chat-memory design.

## Stack
- Backend: Flask + SQLAlchemy (`backend/`)
- Frontend: React (`matoso-chatbot/`)
- LLM runtime: `llama.cpp` server exposing an OpenAI-compatible API
- Local model: `gpt-oss-20b` GGUF served as `local-model`

## Backend layout
- `backend/config.py`: app configuration and environment parsing
- `backend/extensions.py`: Flask extension instances
- `backend/models.py`: SQLAlchemy models
- `backend/db_schema.py`: schema/index compatibility helpers
- `backend/routes/`: auth/chat/progress route handlers
- `backend/utils.py`: auth/session and shared error helpers
- `backend/services/`: prompt building, chat memory, app search, and `llama.cpp` integration

## 1. Prerequisites
Install these first:
- Git
- Python 3.12+
- Node.js 18+ and npm
- CMake
- A C/C++ build toolchain for building `llama.cpp`

## 2. Clone
```bash
git clone <your-repo-url>
cd Lalmba_Capstone_Project
```

## 3. Install and build `llama.cpp`

This project expects a locally built `llama-server` binary.

Recommended layout:
- Keep this repository and `llama.cpp` as sibling folders on your laptop.
- Example:
  - `<workspace>/Lalmba_Capstone_Project`
  - `<workspace>/llama.cpp`

The README examples assume `llama-server` is available at a path like:
- `../llama.cpp/build/bin/llama-server`

Recommended local-dev install flow:

```bash
cd <workspace>
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake .. -DGGML_CUDA=ON -DLLAMA_OPENSSL=ON
cmake --build . --config Release
```

This enables CUDA support and builds `llama.cpp` with OpenSSL support.

Confirm the server binary exists:

```bash
ls ../build/bin/llama-server
```

The backend talks to the OpenAI-compatible `llama-server` HTTP API. It is not enough to have only the CLI tools built; `llama-server` must be available and running.

## 4. Set up the `gpt-oss-20b` GGUF model

This project currently uses a `gpt-oss-20b` GGUF model file such as:
- `/path/to/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf`

One way to download the model with `llama.cpp` is:

```bash
./bin/llama-cli -hf ggml-org/gpt-oss-20b-GGUF --threads 4 --n-gpu-layers 6
```

That command downloads the `gpt-oss-20b` GGUF from Hugging Face using `llama.cpp`. After download, find the GGUF path on your machine and use that path with `llama-server -m`.

Requirements:
- The GGUF file must exist on disk before starting the local model server.
- The model must be served with alias `local-model`.
- The backend assumes `llama.cpp` is reachable at `http://127.0.0.1:8080`.

If your model lives elsewhere, update the startup command or set `LLAMA_CPP_MODEL_PATH` when using the helper script.

## 5. Start `llama.cpp` server

Primary workflow: run the exact command below from the project root so the backend can reach the local model server.

```bash
../llama.cpp/build/bin/llama-server \
  -m /path/to/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf \
  -a local-model \
  -t 4 \
  -ngl 4 \
  --host 127.0.0.1 \
  --port 8080
```

What matters in this command:
- `../llama.cpp/build/bin/llama-server`: local server binary
- `-m ...gguf`: exact model file path
- `-a local-model`: model alias the backend calls
- `-t 4`: CPU thread count
- `-ngl 4`: GPU layers to offload
- `--host 127.0.0.1 --port 8080`: API address the backend expects

Secondary helper flow:

```bash
export LLAMA_CPP_SERVER_BIN=/absolute/path/to/llama.cpp/build/bin/llama-server
export LLAMA_CPP_MODEL_PATH=/absolute/path/to/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf
export LLAMA_CPP_HOST=127.0.0.1
export LLAMA_CPP_PORT=8080
export LLAMA_CPP_MODEL_ALIAS=local-model
./scripts/start_llama_cpp.sh
```

The helper script is fine for basic startup, but it does not expose the full recommended runtime flags from the main command such as `-t 4` and `-ngl 4`.

Verify `llama-server` is reachable:

```bash
curl http://127.0.0.1:8080/v1/models
```

The returned model list should include `local-model`.

## 6. Python environment (single root `.venv`)

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

Backend startup also initializes:
- a local app-search embedding index
- Chroma-based chat memory storage
- rolling conversation state tables and indexes

## 7. Frontend dependencies
```bash
cd matoso-chatbot
npm install
cd ..
```

## 8. Environment variables
Defaults work for local dev, but these can be set if needed.

Backend core:
- `FLASK_SECRET_KEY`
- `DATABASE_URL` (default local SQLite)
- `CORS_ORIGINS` (default includes `http://localhost:3000`)
- `FLASK_DEBUG` (`true` or `false`)
- `LOG_LEVEL`
- `LOG_FULL_PROMPTS` (default `false`; logs full system and user prompts for debugging)

`llama.cpp` runtime:
- `LLAMA_CPP_BASE_URL` (default `http://127.0.0.1:8080`)
- `LLAMA_CPP_MODEL_ALIAS` (default `local-model`)
- `LLAMA_CPP_MODEL_PATH` (required by `scripts/start_llama_cpp.sh`)
- `LLAMA_CPP_MAX_ATTEMPTS`
- `LLAMA_CPP_SERVER_BIN` (the codebase has a machine-specific default; set this explicitly on your machine if your `llama.cpp` binary is elsewhere)
- `LLAMA_CPP_HOST` (default `127.0.0.1`)
- `LLAMA_CPP_PORT` (default `8080`)

App search:
- `APP_MANIFEST_PATH` (default `backend/data/app_manifest.json`)
- `APP_EMBEDDING_MODEL` (default `all-MiniLM-L6-v2`)
- `APP_MATCH_THRESHOLD` (default `0.35`)
- `APP_SEARCH_ENABLED` (default `true`)

Hybrid multi-turn memory:
- `CHAT_MEMORY_ENABLED` (default `true`)
- `CHAT_MEMORY_EMBEDDING_MODEL` (defaults to `APP_EMBEDDING_MODEL`)
- `CHAT_MEMORY_PERSIST_DIR` (default `backend/data/chat_memory_chroma`)
- `CHAT_MEMORY_COLLECTION_NAME` (default `chat_memory`)
- `CHAT_MEMORY_TOP_K` (default `5`)
- `CHAT_MEMORY_SCORE_THRESHOLD` (default `0.35`)
- `CHAT_MEMORY_ANCHOR_CHAR_BUDGET` (default `1200`)
- `CHAT_MEMORY_FIFO_TURNS` (default `3`)
- `CHAT_QUESTION_LIMIT` (default `10`)
- `CHAT_SUMMARY_WINDOW_TURNS` (default `5`)
- `CHAT_SUMMARY_OVERLAP_TURNS` (default `1`)

Frontend:
- `REACT_APP_API_BASE` (default `http://localhost:5000` in React dev mode, same-origin when served by Flask)

## 9. Run the app

Dependency order:
1. Install and build `llama.cpp`.
2. Place or download the `gpt-oss-20b` GGUF model.
3. Start `llama-server`.
4. Start the backend.
5. Start the frontend.

From the project root, start the services in separate terminals.

Terminal 1 (`llama.cpp`):

```bash
cd Lalmba_Capstone_Project
../llama.cpp/build/bin/llama-server \
  -m /path/to/ggml-org_gpt-oss-20b-GGUF_gpt-oss-20b-mxfp4.gguf \
  -a local-model \
  -t 4 \
  -ngl 4 \
  --host 127.0.0.1 \
  --port 8080
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

## 10. Local Wi-Fi deployment for Endless laptops

For the Dell-as-server deployment, do not run the React dev server on the Endless laptops.
Build the frontend on the Dell once, then let Flask serve it from the same origin as the backend.

Build the frontend on the Dell:

```bash
cd Lalmba_Capstone_Project
./scripts/build_frontend.sh
```

Start the local services on the Dell:

```bash
cd Lalmba_Capstone_Project
./run_all.sh
```

Then open the Dell from any Endless laptop on the same Wi-Fi:

```text
http://<dell-local-ip>:5000
```

Notes:
- `run_all.sh` now expects the frontend build to already exist.
- `llama.cpp` still stays private to the Dell backend.
- Browser clients use one URL for both UI and API, which avoids cross-origin cookie issues.

## 11. Multi-turn chat design

The chat flow is now a hybrid memory system instead of a simple recent-history prompt.

Flow:
1. The user sends a message to `POST /chat/message`.
2. The backend loads that user's rolling conversation state.
3. Recent turns are read from a small in-process FIFO buffer.
4. Older archived turns are retrieved from Chroma using semantic similarity.
5. The current rolling summary is included when one exists.
6. The prompt is built from the current query, recent turns, retrieved memory, rolling summary, and optional app context.
7. The backend sends that prompt to the local OpenAI-compatible `llama.cpp` endpoint.
8. The new exchange is stored in SQL, archived into Chroma, and appended to the recent-turn buffer.
9. After enough turns, the rolling summary is refreshed.

Persistence layers:
- `messages`: visible chat history
- `conversations`: rolling summary and session counters
- Chroma collection: archived semantic memory for retrieval

Important behavior:
- Recent turns are short-term context only and are kept in-process.
- Retrieved Chroma memories are filtered by `user_id`, similarity threshold, and character budget.
- Rolling summaries are refreshed after `CHAT_SUMMARY_WINDOW_TURNS`.
- Summary refresh uses overlap turns controlled by `CHAT_SUMMARY_OVERLAP_TURNS`.
- Control/app-choice turns are filtered out when reconstructing turns for summary generation.
- Each chat session enforces a question cap using `CHAT_QUESTION_LIMIT`.

## 12. API reference

Auth:
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /auth/session` (alias)

Chat:
- `POST /chat/message`
  - returns `messages` and `session`
- `GET /chat/history`
  - returns `history` and `session`
- `POST /chat/reset`
  - clears chat history, progress, rolling conversation state, and user chat-memory entries

Session metadata returned by chat endpoints:
- `question_count`
- `question_limit`
- `questions_remaining`
- `limit_reached`

Question-limit behavior:
- Once the limit is reached, the backend stops creating a normal tutor reply for new questions.
- It returns an assistant message telling the user to reset the session before starting a new lesson.

Progress:
- `GET /progress`
- `POST /progress`
- `POST /progress/reset`

## Local app manifest

The backend loads local app metadata from:
- `backend/data/app_manifest.json`

Each manifest entry must include:
- `app_id`
- `name`
- `description`
- `tutorial_steps`

Optional semantic fields:
- `aliases`
- `tags`

On server startup, the backend validates this file and builds an in-memory vector index from a normalized semantic profile for each app. That profile combines the app name, description, aliases, and tags so indirect requests can match more reliably.

## 13. Test commands

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

## 14. Troubleshooting
- `Cannot connect to server` in frontend:
  - confirm backend is running on `:5000`
  - confirm `REACT_APP_API_BASE` if non-default
- Backend starts but replies fail:
  - confirm `llama-server` is running on `127.0.0.1:8080`
  - confirm your `llama-server` binary exists and is executable
  - confirm your `gpt-oss-20b` GGUF model file exists at the path you passed with `-m`
  - confirm `curl http://127.0.0.1:8080/v1/models` returns `local-model`
  - confirm backend `LLAMA_CPP_BASE_URL` matches the server host and port
  - confirm model alias is `local-model`
- Chat context seems wrong:
  - confirm `CHAT_MEMORY_ENABLED=true`
  - confirm Chroma persist directory is writable
  - confirm summary and question-limit settings are not overly restrictive
- CORS errors in browser:
  - ensure frontend origin is present in `CORS_ORIGINS`
- `pytest: command not found`:
  - activate root `.venv`
  - install dependencies again with `pip install -r backend/requirements.txt`
