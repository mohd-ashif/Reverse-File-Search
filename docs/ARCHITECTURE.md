# Architecture

## 1. System Overview

Reverse File Search is a two-tier web application:

```
┌─────────────┐      HTTP/JSON, SSE, WS      ┌──────────────┐      SQL       ┌────────────┐
│  Frontend   │ ───────────────────────────► │   Backend    │ ─────────────► │ PostgreSQL │
│  (React)    │ ◄─────────────────────────── │  (FastAPI)   │                │ (metadata) │
└─────────────┘                              └──────┬───────┘                └────────────┘
                                                     │
                                          embeddings  │  chat completions
                                                     ▼                    ▼
                                              ┌────────────┐      ┌──────────────┐
                                              │   Chroma   │      │  Groq Cloud  │
                                              │ (vectors)  │      │ (LLM, opt.)  │
                                              └────────────┘      └──────────────┘
```

- **Frontend** — a React SPA (Vite) that drives folder management, file browsing, and an AI chat interface. Talks to the backend over plain REST, Server-Sent Events (streamed chat), and a raw WebSocket (live scan progress).
- **Backend** — a FastAPI service owning all business logic, persistence, the indexing pipeline, and every LLM interaction.
- **PostgreSQL** — the single relational store for all structured metadata (folders, files, chunks, entities, summaries, tags, search history).
- **Chroma** — a persistent, embedded vector store (`backend/storage/chroma/`) holding chunk embeddings, queried for nearest-neighbor retrieval.
- **Groq Cloud** — the only external network dependency; entirely optional. If `GROQ_API_KEY` is unset, every AI-backed feature (query rewriting, tagging, entity extraction, summaries, AI answers, search suggestions) degrades gracefully to "not available" without breaking anything else.

## 2. Backend Layering

Strict layered architecture, enforced by convention (not by tooling):

```
endpoint  →  service  →  repository  →  model
(HTTP)       (business logic)  (data access)  (ORM/table)
```

- **`api/v1/endpoints/*`** — routing and request/response marshalling only. No business logic. Each file is one resource (`folders`, `files`, `search`, `ws`, `health`).
- **`schemas/*`** — Pydantic models for request/response validation, deliberately decoupled from the ORM models so API contracts can evolve independently of storage.
- **`services/*`** — all business logic; orchestrates one or more repositories, external clients (Groq, Chroma, sentence-transformers), and other services.
- **`repositories/*`** — the only layer allowed to write SQLAlchemy queries; isolates persistence details from services.
- **`models/*`** — SQLAlchemy ORM table definitions (see §4 Data Model).
- **`core/*`** — cross-cutting config (`config.py`, environment-driven `Settings`) and logging setup.

Schema changes always go through Alembic (`backend/alembic/versions/`) — never hand-edit the database.

## 3. Backend Service Map

| Service | Responsibility |
|---|---|
| `FolderService` | Register/list/remove monitored folders; path validation; scan estimates |
| `FileScannerService` | Recursively walks a folder, reconciles `indexed_files` with disk state (added/modified/deleted/skipped/sensitive), emits progress via `ScanProgressTracker` |
| `IndexingPipeline` | Extracts text from pending files, chunks it, embeds chunks into Chroma, then best-effort triggers entity extraction and tag classification |
| `SearchService` | Embeds a query (after optional rewriting) and performs similarity search against Chroma; also supports folder-scoped and single-file-scoped retrieval |
| `SearchStreamService` | Composes `SearchService` retrieval with `AnswerStreamService` into one SSE response for `/search/stream` |
| `AnswerService` / `AnswerStreamService` | Turn retrieved chunks into a grounded, cited answer (non-streaming JSON mode / streaming SSE) |
| `QueryRewriteService` | Groq-backed pre-retrieval query rewriting (expands acronyms/short queries) |
| `SearchSuggestionService` | Backs the search box's autocomplete: recent/popular searches (from `search_query_logs`) plus AI-generated suggestions |
| `EntityExtractionService` | Extracts structured business fields (invoice number, GST, vendor, amount, dates, …) from a file's text via Groq |
| `TagExtractionService` | Classifies a file's text into category tags (Invoice, Contract, Resume, Tax, Purchase Order, Medical Record, Salary Slip, Bank Statement, Receipt, Letter, or a custom one) via Groq |
| `SummaryService` / `FileSummaryService` | Generates and persists a structured summary (executive summary, key points, dates, people, orgs, risks, action items) for a single file, on demand |
| `FileService` | Read access to indexed files, tags |
| `ChunkRepository` / `FileRepository` / `FolderRepository` / `TagRepository` / `SearchQueryRepository` / `EntitiesRepository` / `SummaryRepository` | Data access layer, one per aggregate |
| `sensitive_file_detector` | Flags credential/key-like files so they're excluded from indexing by default |
| `folder_access_guard` / `folder_path_guard` | Filesystem-level validation (existence, permissions, network/lock errors, overly-broad paths) |
| `GroqClient` | Thin transport wrapper around Groq Cloud's OpenAI-compatible chat completions API (JSON mode + token streaming) — the only class that talks to Groq's HTTP API |
| `rag_context` | Shared grounding logic (context building, insufficient-context fallback message, similarity-based confidence, history trimming) used by both answer services |
| `vector_store` (`ChromaVectorStore`) | Wraps the persistent Chroma collection: upsert, delete, similarity query (with optional metadata `where` filter), get-by-id |
| `embedding_service` | Lazy-loads the `sentence-transformers` model and embeds text |
| `scan_progress` / `ws_manager` | Tracks and broadcasts live scan/index progress over a per-scan WebSocket feed |
| `chunking` | Splits extracted text into overlapping, word-count-bounded chunks |
| `extractors` | Per-file-type text extraction (PDF, DOCX, TXT, Markdown, Excel, image OCR) |
| `file_type_detector` | Maps file extension → `FileType` enum; defines the supported-extension allowlist |

## 4. Data Model

### 4.1 Relational schema (PostgreSQL)

```
monitored_folders 1───* indexed_files 1───* file_chunks
                                      1───1 document_entities
                                      1───1 file_summaries
                                      1───* file_tags

search_query_logs   (independent, append-only)
users               (reserved, not yet used by any endpoint)
```

| Table | Key columns | Notes |
|---|---|---|
| `monitored_folders` | `id`, `path` (unique), `is_active`, timestamps | Root of a monitored tree |
| `indexed_files` | `id`, `folder_id` (FK, cascade delete), `absolute_path` (unique), `filename`, `extension`, `file_type` enum, `size_bytes`, `checksum`, `mtime`, `status` enum, `error_message` | `status`: `pending` → `extracted` → `embedded`, or `failed` |
| `file_chunks` | `id`, `file_id` (FK, cascade delete), `chunk_index`, `chroma_id` (unique), `char_count` | 1:1 with a Chroma vector entry |
| `document_entities` | `id`, `file_id` (FK, unique, cascade delete), `invoice_number`, `vendor`, `customer`, `gst`, `pan`, `amount`, `date`, `email`, `phone`, `address`, `bank`, `po_number`, `contract_number` | All fields nullable; populated best-effort after indexing |
| `file_summaries` | `id`, `file_id` (FK, unique, cascade delete), `executive_summary`, `key_points` (JSON list), `important_dates`, `people`, `organizations`, `risks`, `action_items`, `model` | Generated on demand (`POST /files/{id}/summary`), not automatically at index time |
| `file_tags` | `id`, `file_id` (FK, cascade delete), `tag` (unique per file+tag) | 0..N per file; regenerated wholesale (`replace_tags`) each time a file is (re-)indexed |
| `search_query_logs` | `id`, `query_text` | Append-only; every `/search/` and `/search/stream` request logs its query text, used to derive recent/popular suggestions |
| `users` | `id`, `email` (unique), `hashed_password`, `full_name`, `is_active` | Model exists; no auth flow uses it yet |

All tables inherit `id` (PK), `created_at`, `updated_at` from `TimestampMixin`.

### 4.2 Vector store (Chroma)

- One persistent collection (default name `file_chunks`) at `CHROMA_PERSIST_DIR` (default `backend/storage/chroma/`).
- Configured for cosine distance (`hnsw:space: cosine`).
- Each entry's metadata: `{file_id, folder_id, absolute_path, chunk_index}` — `folder_id` is what enables folder-scoped chat to filter retrieval via a Chroma `where` clause.
- Each entry corresponds 1:1 to a `file_chunks` row via `chroma_id`. Deleting a file, deleting a folder, or reclassifying a file as sensitive removes both sides together.

> **Caveat:** `folder_id` metadata was added after the vector store was first populated. Chunks embedded before that change won't match a folder-scoped chat filter until the file is re-indexed (rescan the folder).

## 5. Indexing Pipeline (end to end)

Triggered per-file by a scan (`FileScannerService` marks new/changed files `pending`, then `IndexingPipeline.process_pending()` picks them up):

1. **Extract** — `extractors.get_extractor(file_type)` pulls raw text (PDF via PyMuPDF, DOCX via python-docx, TXT/Markdown read directly, Excel via a spreadsheet reader, images via Pillow + pytesseract OCR). Failure → `status=failed`, `error_message` set, pipeline stops for that file.
2. **Chunk** — `chunking.chunk_text()` splits into ~500-word chunks with 50-word overlap (configurable).
3. **Embed** — `embedding_service` (sentence-transformers `all-MiniLM-L6-v2` by default) embeds each chunk. Failure → `status=failed`.
4. **Store** — chunks upserted into Chroma with `{file_id, folder_id, absolute_path, chunk_index}` metadata; `FileChunk` rows created in Postgres. `status=embedded`.
5. **Best-effort enrichment** (never allowed to flip a successfully-embedded file back to `failed`):
   - `_extract_entities_safely` — `EntityExtractionService.extract(text)` → upserts `document_entities` if Groq is configured and returns data.
   - `_generate_tags_safely` — `TagExtractionService.extract(text)` → `TagRepository.replace_tags(file_id, tags)` if Groq is configured and returns tags.

Both enrichment steps log and swallow any exception; a Groq outage never affects file indexing status.

Summaries are **not** generated automatically — they're generated on demand via `POST /files/{file_id}/summary` (frontend: opening a file's detail dialog and requesting a summary).

## 6. Search & Chat Architecture

### 6.1 Retrieval scoping

`SearchService.retrieve_for_query()` is the single entry point used by both `/search/` and `/search/stream`, and resolves scope with this precedence:

1. **`file_id` set** → `retrieve_file()`: returns the file's *entire* chunk set (in document order, not similarity-ranked), up to a cap (40 chunks / 24,000 chars). Bypasses embedding search entirely — chosen because single-file Q&A ("explain clause 4", "who signed?") needs exact content, not whatever a top-k similarity search happens to surface.
2. **`folder_id` set** (and no `file_id`) → `retrieve()` with a Chroma `where={"folder_id": ...}` filter, still similarity-ranked.
3. **Neither set** → global similarity search across all indexed content.

### 6.2 Query rewriting

Before an unscoped/folder-scoped embedding search, `QueryRewriteService` optionally rewrites the raw query via Groq (e.g. `"GST"` → `"GST invoices issued during financial year"`) to improve recall on short/acronym-heavy queries. Skipped entirely for file-scoped chat (nothing to rewrite for retrieval since the full file is used directly). Falls back to the original query on any failure or when disabled/unconfigured.

### 6.3 Answer generation

- **Non-streaming** (`POST /search/`, `generate_answer: true`): `AnswerService` calls Groq once in JSON mode, returns `{text, sources, confidence}`. Confidence is self-reported by the model, validated against a `sufficient` flag.
- **Streaming** (`POST /search/stream`, always generates an answer): `AnswerStreamService` emits SSE frames in order — `query` → `results` → `meta` (sources + similarity-derived confidence) → zero or more `token` → `done`/`error`.
- Both are pure post-processing over already-retrieved `SearchResultItem`s (`rag_context.build_context`) — a disabled/unreachable Groq degrades to "no AI answer", never breaks retrieval.
- Grounding is enforced by system prompt: only retrieved excerpt text is shown to the model; sources are taken from retrieval metadata, never the model's own output (so citations can't be hallucinated); insufficient context yields the exact fallback string `"I couldn't find enough information."`.

### 6.4 Conversation memory

- Stateless on the server — every request carries its own `history: [{role, content}, ...]`; nothing conversational is persisted in the database.
- The frontend (`useChat` hook) holds the full turn list in React state, sends only the last 20 messages, excludes any turn that isn't `done` (in-progress/errored/cancelled), and the server additionally caps history to the most recent 12 messages regardless of what's sent.
- **Scoped conversations are isolated**: `useChat({ folderId, fileId })` is a distinct hook instance per scope. The chat page remounts its conversation component (`key={folderId}`) when the folder scope changes, and the file-chat panel is keyed by `file.id`, so switching folders/files never leaks turns from a different scope into the model's context.

### 6.5 Search suggestions

`SearchSuggestionService.get_suggestions(q)` returns three lists, refreshed as the user types (debounced 250ms client-side):
- `recent` / `popular` — derived from `search_query_logs` (grouped/ordered SQL queries, optionally prefix-filtered by what's typed so far).
- `ai_generated` — Groq-generated example queries, aware of the file categories in use; adapts between "generic starter suggestions" (empty box) and "complete what I'm typing" (partial input).

## 7. Real-time Scan Progress

`POST /folders/{id}/scan/start` returns a `scan_id` immediately and runs the scan + index in a background thread (the scan/index pipeline itself is synchronous code, not async). The frontend opens a WebSocket to `/ws/scan/{scan_id}` (`ws_manager.ScanConnectionManager`) and receives:

- `progress` events per file/stage (`finding_files → reading_metadata → extracting_text → generating_embeddings → saving_to_database → finalizing`), with running totals and an ETA.
- One terminal `summary` event (counts + per-file failures) or `error` event.

`ScanProgressTracker` runs on the background thread and hands each broadcast to the FastAPI event loop via `asyncio.run_coroutine_threadsafe`, since the tracker itself isn't async.

The older synchronous `POST /folders/{id}/scan` (no progress feed, blocks until done) is still available and used by simpler callers/tests.

## 8. Frontend Structure

```
frontend/src/
├── api/            axios client + one wrapper module per backend resource
├── components/
│   ├── ui/         shadcn/ui primitives (button, dialog, table, badge, select, progress, …)
│   ├── layout/     AppLayout (nav shell), ThemeToggle
│   └── common/     MarkdownContent (GFM + code blocks), TypingIndicator, ErrorBoundary
├── features/
│   ├── folders/    AddFolderDialog, FolderRowActions, FolderEstimatePreview, ScanProgressDialog, RiskBadge
│   ├── files/       FileDetailDialog, FileSummarySection, FileChatPanel, TagBadge
│   ├── chat/         ChatInput, ChatMessageBubble, SourceCitations, SuggestedQuestions, SearchSuggestionsDropdown
│   └── onboarding/    GettingStarted (first-run guidance on the Overview page)
├── hooks/          useFolders, useFiles, useChat, useScanSocket, useSearchSuggestions, useTheme, useDebounce
├── lib/            cn (class merge), status (badge label/variant maps, formatters), tagColors, tagIcons, sse (SSE parsing), ws (WebSocket URL helper)
├── pages/          HomePage, FoldersPage, FilesPage, ChatPage, NotFoundPage
├── router/          React Router route table
└── types/          IndexedFile, Folder, scan events, search/chat types, tag types, search-suggestion types
```

State management is deliberately simple: TanStack Query for all server state (folders/files/tags, cached and invalidated per mutation), local `useState`/custom hooks for UI/conversation state. No global client-state store is in active use (Zustand is a listed dependency but nothing currently uses it).

## 9. Deployment

- `docker-compose.yml` at the repo root runs three services: `db` (Postgres 16), `backend` (`docker/backend.Dockerfile`, port 8000), `frontend` (`docker/frontend.Dockerfile`, port 5173→80). Backend storage (`backend/storage/`, including the Chroma persist dir) is bind-mounted so it survives container recreation.
- Locally, backend and frontend run independently (`uvicorn --reload`, `vite dev`), against a Postgres instance the developer provides.

## 10. Known Caveats (as of this writing)

- **No authentication** — `users` model and `SECRET_KEY`/`ACCESS_TOKEN_EXPIRE_MINUTES` config exist but nothing enforces auth; single-user/trusted-network deployment is assumed.
- **`recent`/`popular` search suggestions are global**, not per-user — there's no session/user concept to partition them by.
- **Folder-scoped chat requires re-indexing** files embedded before folder-scoping was added, since `folder_id` chunk metadata didn't exist yet at that point.
- **Vector distance metric**: the Chroma collection is configured for cosine distance, but if the underlying HNSW index was physically built before that setting took effect (a pre-existing collection), the index itself keeps using whatever metric it was created with — reconfiguring the stored config doesn't retroactively rebuild the index. A full rebuild (wipe `storage/chroma`, rescan) is the only fix if this drifts.
- **Conversation history is never persisted** — by design (see §6.4), not a bug: refreshing the chat page always starts a fresh conversation.
