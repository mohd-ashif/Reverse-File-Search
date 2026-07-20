# Reverse File Search — Backend

FastAPI service that powers the Reverse File Search application: it registers folders to monitor, scans them for supported files, extracts and chunks text, embeds the chunks into a Chroma vector store, and answers semantic search queries against those embeddings.

See the [root README](../README.md) for the overall project overview and the [SRS](../docs/SRS.md) for full requirements.

## Tech Stack

- **FastAPI** — HTTP API layer
- **SQLAlchemy** (ORM) + **Alembic** (migrations)
- **PostgreSQL** — primary relational store (see `DATABASE_URL`)
- **ChromaDB** — persistent vector store for embeddings
- **sentence-transformers** — embedding generation (`all-MiniLM-L6-v2` by default)
- **PyMuPDF / python-docx / Pillow + pytesseract / Markdown** — per-file-type text extraction
- **Groq Cloud** (via `httpx`) — optional LLM backend for query rewriting (pre-retrieval) and AI-generated, grounded search answers (streamed via SSE)

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       └── endpoints/     # health, folders, files, search
│   ├── core/                  # config, security, logging
│   ├── db/                    # engine/session, declarative base
│   ├── models/                # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # business logic (scanning, indexing, search, ...)
│   ├── repositories/            # data access layer
│   ├── utils/                  # shared helpers
│   └── main.py                 # FastAPI app entrypoint
├── alembic/                    # migrations
├── storage/
│   ├── uploads/                # (reserved) uploaded file artifacts
│   ├── index/                  # (reserved) search index artifacts
│   └── chroma/                 # Chroma persistent collection
├── tests/
├── requirements.txt
└── alembic.ini
```

Request flow: `endpoint -> service -> repository -> model`.

- **api** — routing and request/response handling only, no business logic
- **schemas** — Pydantic models for validation/serialization, decoupled from ORM models
- **services** — business logic, orchestrates repositories
- **repositories** — data access, isolates SQLAlchemy queries from services
- **models** — SQLAlchemy ORM table definitions
- **core** — cross-cutting config, security, logging

## Prerequisites

- Python 3.12+
- A running PostgreSQL instance (or adjust `DATABASE_URL` to point at one you have)
- (Optional) Tesseract OCR installed, if you want text extraction from images

## Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# edit .env — set a real SECRET_KEY, DATABASE_URL, etc. before any non-local use
```

## Database Migrations

```bash
# apply existing migrations
alembic upgrade head

# after changing a model, generate a new migration
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

- API base: `http://localhost:8000/api/v1`
- Interactive docs (Swagger UI): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Configuration

All settings are defined in `app/core/config.py` (`Settings`, loaded via `pydantic-settings` from `backend/.env`). Key variables:

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Deployment environment label |
| `DEBUG` | `true` | Enables debug behavior |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/reverse_file_search` | SQLAlchemy connection string |
| `STORAGE_DIR` | `./storage` | Root for on-disk storage artifacts |
| `CHROMA_PERSIST_DIR` | `./storage/chroma` | Chroma vector store location |
| `CHROMA_COLLECTION_NAME` | `file_chunks` | Chroma collection name |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | sentence-transformers model used for embeddings |
| `CHUNK_SIZE_WORDS` | `500` | Words per chunk during indexing |
| `CHUNK_OVERLAP_WORDS` | `50` | Word overlap between consecutive chunks |
| `TESSERACT_CMD` | *(blank)* | Absolute path to the Tesseract binary; blank uses `PATH` |
| `SCAN_IGNORE_DIR_NAMES` | `__pycache__, node_modules, .git, .venv, venv, .idea, .vscode, System Volume Information, $RECYCLE.BIN, .Trash` | Directory names skipped during a folder scan |
| `LARGE_FILE_THRESHOLD_BYTES` | `50_000_000` | Files at/above this size are flagged as "large" in scan estimates |
| `SECRET_KEY` | `change-me-in-env` | Signing key for auth tokens (not yet wired up) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Auth token lifetime (not yet wired up) |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins for the frontend |
| `GROQ_API_KEY` | *(blank)* | Groq Cloud API key. Leave blank to disable AI-generated answers entirely (search itself keeps working) |
| `GROQ_API_BASE_URL` | `https://api.groq.com/openai/v1` | Groq's OpenAI-compatible API base URL |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model used for both the JSON-mode and streaming answer paths |
| `GROQ_TIMEOUT_SECONDS` | `20.0` | Request timeout for non-streaming Groq calls |

## API Reference

Base prefix: `/api/v1`

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/folders/` | List monitored folders |
| POST | `/folders/` | Register a folder to monitor |
| POST | `/folders/estimate` | Dry-run scan estimate for a path (file counts, size, large/sensitive-file warnings) before committing to it |
| DELETE | `/folders/{folder_id}` | Stop monitoring a folder (and remove its indexed data) |
| POST | `/folders/{folder_id}/scan` | Scan a folder for changes, then index pending files. Accepts `?skip_sensitive=true\|false` (default `true`) |
| GET | `/files/` | List indexed files, optionally filtered with `?folder_id=` |
| GET | `/files/{file_id}` | Get a single indexed file record |
| POST | `/search/` | Reverse file search — rewrites the query via Groq, embeds it, and returns the most similar indexed chunks plus the `rewritten_query` used. Set `generate_answer: true` in the body to also get a non-streamed AI answer (JSON mode) |
| POST | `/search/stream` | Same retrieval (incl. query rewriting), but streams the AI answer as Server-Sent Events (see below). Powers the frontend's chat interface |
| GET | `/search/suggestions` | Search box autocomplete — `?q=` (optional partial text) returns `{recent, popular, ai_generated}` string lists |

Both endpoints accept an optional `history: [{role: "user"|"assistant", content: string}, ...]` in the request body for multi-turn conversations, and an optional `rewrite_query: bool` (default `true`) — see "Query rewriting" and "AI-generated search answers" below.

### Folder scan errors

Registering or estimating a folder validates the path and maps failures to descriptive HTTP responses:

| Condition | Status |
|---|---|
| Invalid / too-broad path (e.g. a drive root) | 400 |
| Path does not exist | 404 |
| Permission denied | 403 |
| Folder locked by another process | 423 |
| Network path unreachable | 503 |
| Folder already monitored | 409 |

### Sensitive file protection

Before indexing, both the estimate and scan endpoints detect files that look like credentials or private keys (`.env*`, `.pem`, `.key`, `.pfx`, `.kdbx`, `wallet.dat`, `id_rsa`/`id_rsa.pub`, `credentials.json`, `passwords.txt`). By default (`skip_sensitive=true`) these are never read, chunked, or embedded — they're excluded from the count of files that get indexed, and any previously-indexed sensitive file is removed on the next scan. Callers may opt in to indexing them anyway via `skip_sensitive=false`. See `app/services/sensitive_file_detector.py`.

### Query rewriting (Groq)

Before embedding, the user's raw query is rewritten via Groq to improve retrieval accuracy — short, acronym-heavy, or ambiguous queries tend to match poorly against chunk text as-is. For example:

| Original query | Rewritten query |
|---|---|
| `GST` | `GST invoices issued during financial year` |

The pipeline is: **user query → Groq rewrites query → embedding → vector search → (optional) answer**. The rewrite is instructed to preserve the original intent — expanding abbreviations and adding likely context terms, never introducing new topics or assumptions the query doesn't support.

This is a pure pre-processing step over retrieval, implemented in `app/services/query_rewrite_service.py` (`QueryRewriteService`) and orchestrated by `SearchService.rewrite_query()`:
- If `GROQ_API_KEY` is unset, or the rewrite call fails for any reason, retrieval falls back to the **original query unchanged** — a broken or unconfigured rewrite step never blocks search.
- Callers can opt out per-request with `rewrite_query: false` in the body (default `true`).
- The **answer generation** step (see below) still receives the user's original query text for its own "Query: ..." framing — only retrieval embeds the rewritten version. Rewriting is retrieval-only, not conversation-facing.
- The query actually used for retrieval is always returned to the caller: as `rewritten_query` in the `POST /search/` response, and as a `query` SSE event (`{"type": "query", "original_query": ..., "rewritten_query": ...}`) sent first over `POST /search/stream`, before the `results` event.

### AI-generated search answers (Groq)

Both `/search/` and `/search/stream` can synthesize a grounded, natural-language answer on top of the retrieved chunks, using Groq Cloud as the LLM backend. This is a pure post-processing step over retrieval — if `GROQ_API_KEY` is unset or Groq is unreachable, search results are returned normally with no answer.

**Multi-turn conversations:** pass prior turns as `history: [{role, content}, ...]` in the request body. Retrieval (the vector search) always embeds only the current `query` — history is not used for retrieval, only appended to the messages sent to the LLM so it can hold a coherent conversation and resolve follow-ups like "what about the other one?". `rag_context.history_to_messages()` caps this to the most recent 12 messages server-side regardless of what the client sends, to bound prompt size. The frontend additionally trims to the last 20 messages before sending, and only includes assistant turns that finished successfully (`status: "done"`) — an in-progress, errored, or cancelled answer is never fed back in as context.

**Grounding rules (enforced via the system prompt, not just requested):**
- The model is only ever shown the text of the retrieved chunks — no outside knowledge.
- Sources are taken directly from the retrieved chunks' filenames, never from the model's own output, so citations can never be hallucinated.
- If the retrieved context doesn't support an answer, the model is instructed to reply with the exact sentence `"I couldn't find enough information."` instead of guessing.

**Non-streaming (`POST /search/` with `generate_answer: true`):** calls Groq once in JSON mode and returns a complete `AIAnswer` object:

```json
{
  "results": [ { "file_id": 1, "filename": "budget.txt", "chunk_text": "...", "score": 0.87 } ],
  "answer": { "text": "...", "sources": ["budget.txt"], "confidence": 0.91 },
  "rewritten_query": "GST invoices issued during financial year"
}
```

Here `confidence` is self-reported by the model (constrained to `[0, 1]` and validated against a `sufficient` flag in the JSON response) — see `app/services/answer_service.py`.

**Streaming (`POST /search/stream`):** returns `text/event-stream`. Retrieval runs once; the response is a sequence of `data: {...}\n\n` frames:

| Event | Payload | When |
|---|---|---|
| `query` | `{"type": "query", "original_query": "...", "rewritten_query": "..."}` | First — before retrieval's results are available |
| `results` | `{"type": "results", "results": [SearchResultItem, ...]}` | Once retrieval (using the rewritten query) completes |
| `meta` | `{"type": "meta", "sources": [...], "confidence": number}` | Before the first token — confidence here is derived deterministically from retrieval similarity scores (not self-reported by the model), since there's no LLM output yet to judge sufficiency from |
| `token` | `{"type": "token", "text": "..."}` | Once per generated token/delta, in order |
| `done` | `{"type": "done"}` | On successful completion |
| `error` | `{"type": "error", "message": "..."}` | If Groq is unreachable, not configured, or the request fails mid-stream |

If retrieval finds nothing, `meta` is sent with empty sources/zero confidence and a single `token` event carries the exact `"I couldn't find enough information."` message — the LLM is never called in that case. Cancelling the client-side request (aborting the fetch) closes the connection; the server-side generator is torn down via `GeneratorExit`, which closes the underlying Groq HTTP stream (see `GroqClient.chat_stream` in `app/services/groq_client.py`).

**Architecture:** `app/services/groq_client.py` (thin Groq HTTP transport, JSON-mode and streaming) → `app/services/query_rewrite_service.py` (pre-retrieval query rewriting) + `app/services/answer_service.py` (non-streaming answer orchestration) / `app/services/answer_stream_service.py` (streaming answer orchestration) → `app/services/search_stream_service.py` (composes query rewriting + retrieval + streaming answer for the `/search/stream` endpoint). Shared grounding logic (context building, the insufficient-context message, similarity-based confidence, history trimming) lives in `app/services/rag_context.py` so the answer paths can't drift apart.

## Data Model (current)

- **monitored_folders** — `id`, `path`, `is_active`, timestamps
- **indexed_files** — `id`, `folder_id` (FK → `monitored_folders`), `absolute_path`, `filename`, `extension`, `file_type`, `size_bytes`, `checksum`, `mtime`, `status`, `error_message`, timestamps
- **file_chunks** — `id`, `file_id` (FK → `indexed_files`), `chunk_index`, `chroma_id`, `char_count`, timestamps

Embeddings themselves live in a Chroma persistent collection (`storage/chroma`), keyed by `chroma_id`; SQL rows track provenance and reconciliation state. Schema evolves via Alembic migrations as features are implemented.

## Core Services

| Service | Responsibility |
|---|---|
| `FolderService` | Register/list/remove monitored folders; path validation and scan estimates |
| `FileScannerService` | Recursively walks a folder, reconciles `indexed_files` with disk state (added/modified/deleted/skipped) |
| `IndexingPipeline` | Extracts text from pending files, chunks it, and embeds chunks into the vector store |
| `SearchService` | Embeds a query and performs similarity search against Chroma, joining results back to file metadata |
| `FileService` | Read access to indexed file records |
| `sensitive_file_detector` | Flags credential/key-like files so they can be excluded from indexing |
| `folder_access_guard` / `folder_path_guard` | Filesystem-level validation (existence, permissions, network/lock errors, overly-broad paths) |
| `GroqClient` | Thin transport wrapper around Groq Cloud's chat completions API (JSON mode and streaming) |
| `QueryRewriteService` | Rewrites the user's query via Groq before it's embedded, to improve retrieval on short/ambiguous queries; falls back to the original query if disabled or unavailable |
| `AnswerService` | Non-streaming grounded answer synthesis (JSON mode) for `POST /search/` |
| `AnswerStreamService` | Streaming grounded answer synthesis (SSE) — the core of `POST /search/stream` |
| `SearchStreamService` | Composes `SearchService.retrieve()` with `AnswerStreamService` into one SSE response |
| `rag_context` | Shared grounding logic (context building, insufficient-context message, similarity-based confidence) used by both answer services |

## Testing

```bash
pytest
```

## Not Yet Implemented

- Authentication / authorization flows (models and config scaffolding exist; no active auth enforcement yet)
- File upload ingestion (folders are monitored in place; direct upload is not the primary flow)
