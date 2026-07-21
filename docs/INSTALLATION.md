# Installation Guide

## Prerequisites

- Python 3.12+
- Node.js 20+ and npm 10+
- PostgreSQL 14+ reachable from the backend (a `docker-compose` Postgres service is provided if you don't have one)
- (Optional) Tesseract OCR — only needed if you want text extraction from image files (`.png`, `.jpg`, `.bmp`, `.tiff`)
- (Optional) A [Groq Cloud](https://console.groq.com/) API key — only needed for AI features (query rewriting, AI answers, tags, entity extraction, summaries, search suggestions). Everything else (folder scanning, indexing, plain semantic search) works without it.
- (Optional) Docker + Docker Compose, for the containerized setup

## 1. Configure Environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
- Set a real `SECRET_KEY` before any non-local use (reserved for future auth; not yet enforced).
- Set `DATABASE_URL` to point at your Postgres instance.
- Set `GROQ_API_KEY` if you want AI features enabled.

## 2. Backend Setup (local)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
# or, for running the test suite too:
pip install -r requirements-dev.txt

# Apply all migrations (creates every table: folders, files, chunks,
# entities, summaries, tags, search query log)
alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

## 3. Frontend Setup (local)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and calls the backend at `VITE_API_BASE_URL` (defaults to `/api/v1`, proxied to the backend — check `vite.config.ts` if you need a different target).

## 4. Running with Docker

From the project root:

```bash
docker compose up --build
```

This brings up three services: `db` (Postgres 16), `backend` (port 8000), `frontend` (port 5173 → container port 80). Backend storage (`backend/storage/`, including the Chroma vector store and any extracted artifacts) is bind-mounted from `./backend/storage`, so it survives container rebuilds. The backend's `env_file` is `backend/.env` — make sure it exists before running (step 1).

## 5. Database Migrations

Create a new migration after changing a model:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Current migration history (chronological): initial schema (folders, indexed files, chunks) → add `document_entities` table → add `file_summaries` table → add `file_tags` table → add `search_query_logs` table.

## 6. Running Tests

```bash
cd backend
pytest
```

Tests run against the real Postgres database configured in `.env`, wrapped in a transaction that's always rolled back — no test data is left behind, but a reachable, migrated database is required.

Frontend type-checking:
```bash
cd frontend
npx tsc --noEmit -p .
```

## Notes

- **Storage layout:** the Chroma vector store persists at `backend/storage/chroma/`; nothing else under `storage/` is required for the app to function.
- **First run / embedding model:** the sentence-transformers embedding model (`all-MiniLM-L6-v2` by default) downloads and caches on first use — this requires network access the first time (or a pre-populated Hugging Face cache).
- **Without a Groq API key**, the app is still fully usable: folder scanning, indexing, and plain semantic search all work. You'll just see: no query rewriting (searches use your literal text), no AI-generated chat answers, no automatic tags/entities, no on-demand summaries, and no AI-generated search suggestions (recent/popular suggestions still work, since those come from your own search history, not Groq).
- **OCR:** if `TESSERACT_CMD` is unset, the system looks for `tesseract` on `PATH`. Without it, image files are still indexed as files but text extraction from them will fail/return empty text.
