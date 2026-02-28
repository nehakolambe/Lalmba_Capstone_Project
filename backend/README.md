# Mama Akinyi Chatbot Backend

Flask API that powers the Matoso React chatbot. Runs fully offline with:
- SQLite for users/messages/progress
- Ollama for local chat + embeddings
- Chroma for local vector search (RAG)

## Features
- `/auth/register` creates a user with PIN authentication.
- `/auth/login` authenticates and sets a session cookie.
- `/auth/me` returns the current user.
- `/chat/message` stores messages, retrieves app context, calls Ollama, returns sources.
- `/chat/history` returns per-user history.
- `/chat/reset` clears per-user history.
- `/progress` stores learning milestones.
- `/kb/ingest` ingests Markdown app docs into Chroma.
- `/kb/status` shows the KB ingest status.

## Setup (offline)
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python server.py  # runs on http://localhost:5000
```

## Ollama models
Pull the chat and embedding models locally:
```powershell
ollama pull llama2
ollama pull nomic-embed-text
```

## Ingest the knowledge base
```powershell
python backend/scripts/ingest.py --source knowledge_base/apps --persist backend/data/chroma --reset
```

## Environment variables
- `FLASK_SECRET_KEY` - session signing key.
- `DATABASE_URL` - alternate database URI (e.g., `sqlite:///my.db`).
- `CORS_ORIGINS` - comma-separated list of allowed frontend origins.
- `OLLAMA_BASE_URL` - Ollama host/port (default `http://localhost:11434`).
- `OLLAMA_DEFAULT_MODEL` - chat model (default `llama2`).
- `OLLAMA_TIMEOUT_SECONDS` - max wait for Ollama generation calls (default `120`).
- `OLLAMA_FALLBACK_ENABLED` - return a basic offline reply when Ollama is unavailable (default `true`).
- `OLLAMA_EMBED_MODEL` - embedding model (default `nomic-embed-text`).
- `CHROMA_PERSIST_DIR` - Chroma storage (default `backend/data/chroma`).
- `CHROMA_COLLECTION` - Chroma collection (default `app_knowledge`).

## Example requests
### Send a chat message
```http
POST /chat/message
Content-Type: application/json

{
  "text": "How do I export a document as PDF in LibreOffice?"
}
```

### Ingest knowledge base
```http
POST /kb/ingest
Content-Type: application/json

{
  "source_dir": "knowledge_base/apps",
  "persist_dir": "backend/data/chroma",
  "collection": "app_knowledge",
  "reset": true
}
```
