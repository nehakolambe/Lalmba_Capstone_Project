# Lalmba

Offline-first AI tutor for Endless OS laptops (Linux + Endless OS). This repo includes:
- Flask backend (`backend/`) with SQLite, Ollama chat, and offline RAG via Chroma.
- React frontend (`matoso-chatbot/`) for login, chat, and progress tracking.
- App knowledge base (`knowledge_base/apps/`) with Markdown docs.

## What's implemented so far

### Backend (Flask + SQLite)
- Session-based auth with PINs (bcrypt) and endpoints: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` (plus `/auth/session` alias).
- Chat pipeline via `/chat/message`: stores messages, optionally pulls RAG context from Chroma, adds app metadata context from SQLite embeddings, calls Ollama, and returns sources (plus `debug_profile` in development mode).
- Chat history and resets: `/chat/history` and `/chat/reset`.
- Progress tracking: `/progress` (list/add) and `/progress/increment` (capped at 10 steps).
- Onboarding questionnaire storage: `/questionnaire/me` GET/POST, used to personalize chat responses.
- Knowledge base ingestion and status endpoints: `/kb/ingest` and `/kb/status`.
- Debug endpoint to inspect app retrieval: `/debug/apps/search`.
- Basic health check: `/health`.
- Automatic schema checks/migrations on startup via `backend/db_schema.py`.

### RAG + app knowledge
- Markdown knowledge base under `knowledge_base/apps` (Files, Firefox, LibreOffice, Screenshot, Settings).
- RAG pipeline: markdown loader -> chunker -> Ollama embeddings -> Chroma persistence (`backend/data/chroma`).
- App catalog ingestion from Excel (`backend/ingest_apps_excel.py`) into SQLite (`app_docs`, `app_embeddings`) with Ollama embeddings.
- Chat prompts enforce "installed apps only" when answering app recommendation questions.

### Frontend (React)
- Login + registration flow with session bootstrap and a home screen.
- Onboarding questionnaire UI; saved answers drive personalization in chat.
- Chat UI with history load, reset button, help prompt, quick replies, and start cards.
- Typing practice overlay with step-by-step checks and optional progress messages back to chat.
- Read-aloud toggle for assistant replies (Web Speech API if supported).
- RAG source snippets are rendered under assistant replies.
- Progress increments on each successful chat message.

### Scripts, testing, and docs
- `backend/scripts/ingest.py` CLI for knowledge base ingestion into Chroma.
- `backend/questionnaire.py` CLI for collecting onboarding answers and optional Ollama-generated recommendations.
- `scripts/test_personalization.py` to compare responses for two personas (set `FLASK_ENV=development` to see `debug_profile`).
- Demo steps in `docs/demo_checklist.md`.

## Quickstart (offline)
1) Install Ollama and pull models locally:
   - `ollama pull llama2`
   - `ollama pull nomic-embed-text`
2) Ingest the app knowledge base:
   - `python backend/scripts/ingest.py --source knowledge_base/apps --persist backend/data/chroma --reset`
3) Start the backend:
   - `cd backend`
   - `python -m venv venv`
   - `venv/Scripts/activate` (Windows) or `source venv/bin/activate` (Linux)
   - `pip install -r requirements.txt`
   - `python server.py`
4) Start the frontend:
   - `cd matoso-chatbot`
   - `npm install`
   - `npm start`

## Chat flow (Ollama)
```
Browser (React UI)
  -> matoso-chatbot/src/api.js (POST /chat/message)
  -> backend/routes/chat.py
     -> backend/rag/retriever.py (optional RAG via Chroma + Ollama embeddings)
     -> backend/services/ollama_client.py (POST /api/generate)
  <- response saved + returned to UI
```

## Demo checklist
See `docs/demo_checklist.md`.

## How to test personalization

### Automated
1) Start the backend in development mode (so `debug_profile` is returned):
   - Windows (PowerShell): `$env:FLASK_ENV="development"; python backend/server.py`
   - Linux/macOS: `FLASK_ENV=development python backend/server.py`
2) Run the script:
   - `python scripts/test_personalization.py`

Expected output (example):
```
== Personalization Comparison ==
User A profile:
language=English; literacy_level=Beginner; typing_comfort=Low; learning_goals=Improve computer basics; topics=Documents & typing; hours_per_week=1
User A reply (first 300 chars):
...
User B profile:
language=English; literacy_level=Advanced; typing_comfort=High; learning_goals=Spreadsheets, Job readiness; topics=Spreadsheets, Internet & email; hours_per_week=10
User B reply (first 300 chars):
...
OK: Personalization checks passed.
```

### Manual UI
1) Log in as User A.
2) Ask: "Teach me how to use a computer."
3) Observe a simple, step-by-step answer.
4) Log out, log in as User B.
5) Ask the same question.
6) Observe a more advanced, goal-oriented answer (e.g., mentions spreadsheets/job readiness).

## UI Design
- [UI Design Document](docs/UI_DESIGN.md)
- [BDD Scenarios with UI](docs/BDD_WITH_UI.md)
