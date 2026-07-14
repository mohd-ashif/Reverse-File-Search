# Software Requirements Specification (SRS)

## Reverse File Search

**Version:** 1.2
**Status:** Living document — reflects the current implemented feature set plus planned scope
**Date:** 2026-07-14

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for **Reverse File Search**, an AI-powered application that lets a user register local folders for monitoring and then search across their contents using natural-language queries (semantic / "reverse" search), instead of searching by filename or exact keyword match.

It is intended for developers, testers, and reviewers who need a single reference for what the system does, how it is structured, and what constraints it operates under.

### 1.2 Scope

The system:

- Lets a user register ("monitor") one or more local folders.
- Recursively scans each monitored folder, detects new/modified/deleted files, and reconciles an index of file metadata.
- Extracts text from supported file types (PDF, DOCX, TXT, Markdown, Excel, and images via OCR).
- Chunks and embeds extracted text using a sentence-embedding model, storing vectors in a persistent Chroma vector store.
- Detects and, by default, excludes potentially sensitive files (credentials, private keys, `.env` files, etc.) from indexing, with an explicit user override.
- Answers natural-language queries by first rewriting the query for better retrieval (via an LLM), embedding the rewritten query, and retrieving the most semantically similar indexed chunks.
- Optionally synthesizes a grounded, cited natural-language answer from those chunks (via an LLM), across multi-turn conversations.
- Presents all of the above through a web UI: folder management, indexed file browsing, and a chat interface for conversing with an AI grounded in the indexed content.

Out of scope for the current version (see §1.5 Assumptions/Constraints and §8 Future Work):

- User authentication/authorization enforcement (scaffolding exists; not active).
- Multi-user / multi-tenant data isolation.
- Direct file upload as a primary ingestion path (the system indexes files in place from monitored folders).
- Remote/cloud storage backends (local filesystem only).

### 1.3 Intended Audience

- Software engineers implementing or maintaining the system.
- QA engineers writing test plans against these requirements.
- Technical reviewers/stakeholders evaluating feature completeness.

### 1.4 Definitions, Acronyms, Abbreviations

| Term | Meaning |
|---|---|
| **Monitored folder** | A local directory the user has registered for scanning/indexing |
| **Scan** | A recursive walk of a monitored folder that reconciles the database's record of files with what's actually on disk |
| **Indexing / Indexing pipeline** | Extracting text from a file, splitting it into chunks, and embedding those chunks into the vector store |
| **Chunk** | A bounded slice of a file's extracted text (default 500 words, 50-word overlap) that gets its own embedding |
| **Embedding** | A numeric vector representation of text, produced by a sentence-embedding model, used for similarity search |
| **Vector store** | Chroma — a persistent store of embeddings, queried for nearest neighbors to a query embedding |
| **Sensitive file** | A file whose name/extension strongly suggests it holds secrets (e.g. `.env`, `.pem`, `id_rsa`, `credentials.json`) |
| **Query rewriting** | An LLM pre-processing step that expands/clarifies the user's raw query (e.g. resolving acronyms) into a form better suited to embedding-based retrieval, before the vector search runs |
| **Conversation / turn** | A single exchange in the chat interface — a user message or the assistant's response to it; a conversation is an ordered sequence of turns |
| **SRS** | Software Requirements Specification (this document) |

### 1.5 Assumptions and Constraints

- The backend and the folders it monitors run on the same host/filesystem it has direct access to (or an accessible network share); the system does not fetch remote files over HTTP.
- A single-user deployment model is assumed for the current version; there is no per-user data partitioning.
- PostgreSQL is the primary relational datastore for metadata; Chroma is the vector datastore for embeddings. Both must be reachable/writable by the backend process.
- OCR (image text extraction) requires a working Tesseract installation reachable via `PATH` or `TESSERACT_CMD`.

---

## 2. Overall Description

### 2.1 Product Perspective

Reverse File Search is a self-contained two-tier web application:

- **Backend** — a FastAPI service exposing a REST API under `/api/v1`, owning all business logic, persistence, and the embedding/search pipeline.
- **Frontend** — a React single-page app that consumes the backend API and provides the user-facing workflows for folder management, scanning, browsing, and searching.

```
┌─────────────┐      HTTP/JSON       ┌──────────────┐      SQL      ┌────────────┐
│  Frontend   │ ───────────────────► │   Backend    │ ────────────► │ PostgreSQL │
│  (React)    │ ◄─────────────────── │  (FastAPI)   │               │ (metadata) │
└─────────────┘                      └──────┬───────┘               └────────────┘
                                             │
                                             │ embeddings
                                             ▼
                                       ┌────────────┐
                                       │   Chroma   │
                                       │ (vectors)  │
                                       └────────────┘
```

### 2.2 Product Functions (Summary)

1. Register a folder to monitor, with upfront path validation and a scan estimate preview.
2. Scan a monitored folder to detect added/modified/deleted files.
3. Detect potentially sensitive files before indexing and let the user choose whether to skip or include them.
4. Extract text from supported file types and index it (chunk + embed).
5. List and inspect indexed files and their status.
6. Chat with an AI grounded in indexed file content, across multiple turns, with the underlying query rewritten before each retrieval for better recall.
7. Remove a monitored folder (and its indexed data).

### 2.3 User Classes and Characteristics

| User class | Description |
|---|---|
| **End user** | Registers folders, runs scans, searches content. No special technical knowledge required beyond providing a folder path. |
| **Operator/Administrator** | Deploys and configures the backend/frontend (environment variables, database, storage paths), manages the Docker Compose stack. |

Authentication/role separation is not currently enforced (see §1.2, §8).

### 2.4 Operating Environment

- **Backend:** Python 3.12+, FastAPI/Uvicorn, PostgreSQL, ChromaDB persistent store, optional Tesseract OCR binary. Runs on Windows, Linux, or macOS; Docker image provided (`docker/backend.Dockerfile`).
- **Frontend:** Node.js 20+ for development/build; the built static assets are served independently of the backend (or via `docker/frontend.Dockerfile`). Runs in any modern evergreen browser.
- **Deployment:** `docker-compose.yml` at the repo root orchestrates backend + frontend together for local/integrated runs.

### 2.5 Design and Implementation Constraints

- Layered backend architecture is mandatory: `endpoint -> service -> repository -> model`, with Pydantic schemas decoupled from ORM models (see backend README).
- Only the file types in `SUPPORTED_EXTENSIONS` (`app/services/file_type_detector.py`) are eligible for indexing: `.pdf`, `.docx`, `.txt`, `.md`/`.markdown`, `.png`/`.jpg`/`.jpeg`/`.bmp`/`.tiff`/`.tif`, `.xlsx`/`.xls`.
- Certain directory names are always skipped during a scan (`SCAN_IGNORE_DIR_NAMES`): `__pycache__`, `node_modules`, `.git`, `.venv`, `venv`, `.idea`, `.vscode`, `System Volume Information`, `$RECYCLE.BIN`, `.Trash`.
- Hidden/system files (dotfiles, OS hidden/system attribute) are excluded from indexing.
- Sensitive-looking files are excluded from indexing by default (see §3.3).
- Database schema changes must go through Alembic migrations.

### 2.6 Assumptions/Dependencies

See §1.5. Additionally, the embedding model (`all-MiniLM-L6-v2` by default) is downloaded/cached by `sentence-transformers` on first use and must be available (network access on first run, or a pre-populated model cache).

---

## 3. Functional Requirements

Each requirement is numbered `FR-<area>-<n>` and marked with an implementation status.

### 3.1 Folder Management

| ID | Requirement | Status |
|---|---|---|
| FR-FOLD-1 | The system shall allow a user to register a folder for monitoring by providing an absolute filesystem path. | Implemented |
| FR-FOLD-2 | The system shall validate a folder path before registration and reject it with a specific, descriptive error for: missing path, non-directory path, permission denied, path locked by another process, unreachable network location, or an overly broad path (e.g. a drive root). | Implemented |
| FR-FOLD-3 | The system shall reject registering a folder path that is already monitored. | Implemented |
| FR-FOLD-4 | The system shall provide a scan estimate (`POST /folders/estimate`) for a candidate path without persisting anything, returning: total files found, supported vs. unsupported file counts, estimated processing time, estimated storage size, count of large files (≥ configurable threshold), and count/sample of detected sensitive files. | Implemented |
| FR-FOLD-5 | The system shall list all currently monitored folders. | Implemented |
| FR-FOLD-6 | The system shall allow a user to remove a monitored folder, which also removes all of that folder's indexed file records and associated vector-store embeddings. | Implemented |

### 3.2 Scanning and Indexing

| ID | Requirement | Status |
|---|---|---|
| FR-SCAN-1 | The system shall recursively scan a monitored folder's contents, skipping configured ignore-directories and hidden/system files. | Implemented |
| FR-SCAN-2 | The system shall detect and record newly discovered supported files as pending indexing. | Implemented |
| FR-SCAN-3 | The system shall detect files whose modification time has changed since the last scan and re-check their checksum; if the checksum differs, the system shall re-extract/re-embed the file's content and delete its previous chunks/embeddings. If the checksum is unchanged, only the recorded modification time is updated (no re-processing). | Implemented |
| FR-SCAN-4 | The system shall detect files that existed in the index but are no longer present on disk and remove their records and embeddings. | Implemented |
| FR-SCAN-5 | After a scan, the system shall process all pending files through the indexing pipeline: extract text, split it into overlapping word-count-bounded chunks, and embed each chunk into the vector store. | Implemented |
| FR-SCAN-6 | The system shall report scan results as counts of files added, modified, deleted, skipped (unchanged), and skipped-as-sensitive. | Implemented |
| FR-SCAN-7 | The system shall report indexing results as counts of files extracted, embedded, and failed. | Implemented |
| FR-SCAN-8 | Only files with a supported extension shall be eligible for text extraction and embedding; unsupported files are counted but never processed. | Implemented |

### 3.3 Sensitive File Detection

| ID | Requirement | Status |
|---|---|---|
| FR-SENS-1 | The system shall detect files that are likely to contain secrets or credentials, including but not limited to: `.env` and `.env.*` variants, `.pem`, `.key`, `.pfx`, `.kdbx`, `wallet.dat`, `id_rsa`/`id_rsa.pub`, `id_ed25519`/`id_ed25519.pub`, `credentials.json`, `passwords.txt` (case-insensitive match). | Implemented |
| FR-SENS-2 | Sensitive-file detection shall run during both the folder scan estimate and the actual scan, independent of and prior to the hidden-file filter, so that sensitive dotfiles (e.g. `.env`) are still reported rather than silently disappearing into the "hidden" bucket. | Implemented |
| FR-SENS-3 | By default, detected sensitive files shall be excluded from indexing: never opened for text extraction, never chunked, never embedded. | Implemented |
| FR-SENS-4 | If a file was previously indexed and a later scan (with skip-sensitive behavior active) newly classifies it as sensitive, its existing chunks/embeddings shall be removed on that scan (reconciled the same way as a deleted file). | Implemented |
| FR-SENS-5 | The user shall be able to override the default and explicitly choose to index sensitive files for a given scan (`skip_sensitive=false`). | Implemented |
| FR-SENS-6 | When a folder estimate or scan detects one or more sensitive files, the frontend shall display a warning to the user before indexing proceeds, showing the count and up to a few example filenames. | Implemented |
| FR-SENS-7 | When sensitive files are detected ahead of a scan action, the frontend shall present the user with three explicit choices: **Skip sensitive files** (default/primary action), **Continue** (index them anyway), and **Cancel** (do not scan). | Implemented |
| FR-SENS-8 | The default choice, if the user takes no explicit action beyond confirming, shall be to skip sensitive files. | Implemented |

### 3.4 Search

| ID | Requirement | Status |
|---|---|---|
| FR-SRCH-1 | The system shall accept a free-text natural-language query and an optional result limit (`top_k`, default 10). | Implemented |
| FR-SRCH-2 | The system shall embed the query (after query rewriting, see §3.4a) using the same embedding model used for indexing, and perform a similarity search against the vector store. | Implemented |
| FR-SRCH-3 | The system shall return ranked results, each including the source file's ID and filename, the matching chunk's text, and a similarity score. | Implemented |
| FR-SRCH-4 | The frontend shall provide a chat interface where a user enters a query and views the ranked results and any generated answer (see §3.4c). | Implemented |

### 3.4a Query Rewriting

| ID | Requirement | Status |
|---|---|---|
| FR-QR-1 | Before embedding, the system shall optionally rewrite the user's raw query via an LLM (Groq) to improve retrieval accuracy — e.g. expanding acronyms or adding likely context terms (example: "GST" → "GST invoices issued during financial year"). | Implemented |
| FR-QR-2 | The rewrite step shall be instructed to preserve the original query's intent and shall not introduce new topics, assumptions, or specifics not supported by the original query. | Implemented |
| FR-QR-3 | The system shall support disabling query rewriting per-request (`rewrite_query: false`); when disabled, or when no LLM provider is configured, or when the rewrite call fails for any reason, retrieval shall fall back to embedding the original, unmodified query — a failed or disabled rewrite shall never block search. | Implemented |
| FR-QR-4 | The system shall return the query text actually used for retrieval (the rewritten query, or the original if unchanged) to the caller: as `rewritten_query` in the non-streaming response, and as a dedicated `query` event sent before retrieval results in the streaming response. | Implemented |
| FR-QR-5 | The answer-generation step shall reference the user's original query text, not the rewritten form, when framing its response — rewriting affects retrieval only, not the language of the answer. | Implemented |

### 3.4b Conversation History

| ID | Requirement | Status |
|---|---|---|
| FR-CHAT-1 | The system shall support multi-turn conversations: a request may include prior turns as `history: [{role, content}, ...]`, appended to the messages sent to the answer-generating LLM so it can resolve conversational follow-ups. | Implemented |
| FR-CHAT-2 | Conversation history shall not affect retrieval — each turn's vector search shall embed only that turn's (rewritten) query, never prior conversation content. | Implemented |
| FR-CHAT-3 | The system shall cap the number of history messages included in the LLM prompt (12 server-side, regardless of what the client sends) to bound prompt size and cost. | Implemented |
| FR-CHAT-4 | The frontend shall maintain the full conversation as an ordered list of turns, sending only the most recent messages (last 20) as history, and excluding any assistant turn that is in progress, errored, or was cancelled from that history. | Implemented |
| FR-CHAT-5 | The frontend shall allow retrying an individual assistant turn, regenerating it using the conversation history up to (but not including) that turn. | Implemented |

### 3.4c AI-Generated Answers

| ID | Requirement | Status |
|---|---|---|
| FR-AI-1 | The system shall optionally synthesize a natural-language answer from the top retrieved chunks (default top 10) using an LLM (Groq Cloud), returned alongside the normal ranked results. | Implemented |
| FR-AI-2 | The system shall support this via two modes: a non-streaming JSON response (`POST /search/` with `generate_answer: true`) and a streamed response (`POST /search/stream`, Server-Sent Events). | Implemented |
| FR-AI-3 | The model shall be instructed to answer using only the retrieved excerpts and shall never be presented as having access to outside knowledge. | Implemented |
| FR-AI-4 | Answer sources shall be derived deterministically from the filenames of the retrieved chunks, never from the model's own output, so citations cannot be hallucinated. | Implemented |
| FR-AI-5 | If the retrieved context does not support an answer, the system shall return the exact message "I couldn't find enough information." instead of an invented answer, in both the non-streaming and streaming modes. | Implemented |
| FR-AI-6 | The non-streaming mode shall return a confidence score self-reported by the model (constrained to [0, 1]) alongside an explicit sufficiency flag used to decide whether to return the model's answer or the insufficient-context fallback. | Implemented |
| FR-AI-7 | If no AI provider is configured, or the provider is unreachable, normal search results shall still be returned; only the AI answer shall be omitted (non-streaming) or reported via a distinct error event (streaming). | Implemented |
| FR-AI-8 | The streaming endpoint shall emit, over a single connection, in order: the query actually used for retrieval (original vs. rewritten, per §3.4a), the retrieved results, source/confidence metadata (derived from retrieval similarity, since no model output exists yet to self-report from), the answer text as a sequence of token events, then a completion or error event. | Implemented |
| FR-AI-9 | The frontend shall render streamed answer tokens live as they arrive, with a typing indicator shown before the first token. | Implemented |
| FR-AI-10 | The frontend shall allow the user to cancel an in-progress AI answer generation; the in-flight request shall be aborted and the underlying server-side connection to the LLM provider shall be closed. | Implemented |
| FR-AI-11 | The frontend shall allow the user to retry generation after completion, cancellation, or an error, re-running the same query. | Implemented |
| FR-AI-12 | The frontend shall allow the user to copy the generated answer text to the clipboard at any point once any text has been generated. | Implemented |

### 3.4d Chat Interface

| ID | Requirement | Status |
|---|---|---|
| FR-CHATUI-1 | The frontend shall present a single conversational chat interface (not a per-query toggle) as the primary way to search and get answers; every message is sent through the streaming endpoint. | Implemented |
| FR-CHATUI-2 | Assistant responses shall be rendered as Markdown, including GitHub-Flavored Markdown elements (tables, lists, etc.). | Implemented |
| FR-CHATUI-3 | Fenced code blocks within an assistant response shall be visually distinguished (monospace, bordered, labeled with the fence's declared language when present) and shall offer their own copy-to-clipboard control independent of the whole-message copy action. | Implemented |
| FR-CHATUI-4 | Cited source filenames shall be rendered as clickable elements; selecting one that corresponds to a retrieved file shall open that file's detail view. | Implemented |
| FR-CHATUI-5 | When a conversation is empty, the frontend shall present a set of suggested starter questions the user can select instead of typing. | Implemented |
| FR-CHATUI-6 | The message list shall automatically scroll to show new content as it streams in, unless the user has manually scrolled away from the bottom, in which case automatic scrolling shall pause until the user returns to the bottom. | Implemented |
| FR-CHATUI-7 | The frontend shall provide a light/dark theme toggle, persisted across sessions, defaulting to the operating system's preference on first visit. | Implemented |
| FR-CHATUI-8 | The chat layout shall be usable on both desktop and narrow (mobile-width) viewports. | Implemented |

### 3.5 Indexed File Browsing

| ID | Requirement | Status |
|---|---|---|
| FR-FILE-1 | The system shall list indexed files, optionally filtered by monitored folder. | Implemented |
| FR-FILE-2 | The system shall provide detail retrieval for a single indexed file by ID, returning 404 if not found. | Implemented |
| FR-FILE-3 | The frontend shall provide a files page listing indexed files and a detail view showing an individual file's metadata and indexing status. | Implemented |

### 3.6 Health / Operations

| ID | Requirement | Status |
|---|---|---|
| FR-OPS-1 | The system shall expose a health-check endpoint (`GET /health`) suitable for readiness/liveness probes. | Implemented |

### 3.7 Authentication (Planned)

| ID | Requirement | Status |
|---|---|---|
| FR-AUTH-1 | The system shall support user authentication before allowing folder registration, scanning, or search. | Not implemented |
| FR-AUTH-2 | The system shall issue and validate time-limited access tokens (config scaffolding — `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` — already present). | Not implemented |

---

## 4. External Interface Requirements

### 4.1 REST API (Backend)

Base prefix: `/api/v1`. All request/response bodies are JSON.

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| GET | `/health` | — | `{status}` | Health check |
| GET | `/folders/` | — | `FolderRead[]` | List monitored folders |
| POST | `/folders/` | `{path}` | `FolderRead` (201) | Register a folder |
| POST | `/folders/estimate` | `{path}` | `FolderEstimate` | Dry-run scan estimate, incl. sensitive-file detection |
| DELETE | `/folders/{folder_id}` | — | 204 | Remove a monitored folder and its data |
| POST | `/folders/{folder_id}/scan` | query `?skip_sensitive=bool` (default `true`) | `{scan: ScanResult, index: IndexResult}` | Scan + index a folder |
| GET | `/files/` | query `?folder_id=int` (optional) | `IndexedFileRead[]` | List indexed files |
| GET | `/files/{file_id}` | — | `IndexedFileRead` | Get one indexed file (404 if missing) |
| POST | `/search/` | `{query, top_k?, generate_answer?, history?, rewrite_query?}` | `{results: SearchResultItem[], answer: AIAnswer \| null, rewritten_query: string}` | Semantic search (with query rewriting), optionally with a non-streamed AI answer |
| POST | `/search/stream` | `{query, top_k?, history?, rewrite_query?}` | `text/event-stream` — see §4.1.1 | Semantic search (with query rewriting) with a streamed AI answer; powers the chat interface |

Folder-path validation errors are mapped to HTTP status codes: 400 (invalid/too broad), 403 (permission denied), 404 (missing), 409 (already monitored), 423 (locked), 503 (network unreachable).

#### 4.1.1 `/search/stream` event protocol

The response body is a sequence of SSE frames (`data: <json>\n\n`), emitted in this order:

| Event `type` | Payload | Notes |
|---|---|---|
| `query` | `{original_query: string, rewritten_query: string}` | Sent first, before retrieval results — `rewritten_query` equals `original_query` if rewriting was disabled, unavailable, or unchanged |
| `results` | `{results: SearchResultItem[]}` | Sent once retrieval (using the rewritten query) completes |
| `meta` | `{sources: string[], confidence: number}` | Sent before any answer tokens; confidence is derived from retrieval similarity scores, not self-reported by the model |
| `token` | `{text: string}` | Zero or more, in order; concatenation yields the full answer |
| `done` | `{}` | Terminates a successful stream |
| `error` | `{message: string}` | Terminates the stream on failure (not configured, provider unreachable, mid-stream failure) |

### 4.2 Web UI (Frontend)

| Route | Purpose |
|---|---|
| `/` | Landing/overview |
| `/folders` | Register, preview, scan, and remove monitored folders; sensitive-file warning dialogs |
| `/search` | Chat interface: multi-turn conversation grounded in indexed files, with Markdown rendering, code blocks, clickable citations, suggested questions, streamed responses with a typing indicator, per-message cancel/retry/copy, and a light/dark theme toggle (route path retained as `/search`; the nav label is "Chat") |
| `/files` | Browse indexed files and inspect detail |

### 4.3 Configuration Interfaces

Both tiers are configured via `.env` files (see `backend/.env.example`, `frontend/.env.example`) — see backend/frontend READMEs for the full variable list.

---

## 5. Data Requirements

### 5.1 Relational Schema (PostgreSQL, via SQLAlchemy/Alembic)

**monitored_folders**
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| path | string(1024), unique | Absolute, resolved path |
| is_active | bool | default true |
| created_at / updated_at | timestamp | |

**indexed_files**
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| folder_id | int, FK → monitored_folders (cascade delete) | |
| absolute_path | string(2048), unique | |
| filename | string(512) | |
| extension | string(32) | |
| file_type | enum: pdf, docx, txt, markdown, image, excel, unknown | |
| size_bytes | int | |
| checksum | string(64) | Used to detect real content changes vs. mtime-only touches |
| mtime | float | |
| status | enum: pending, extracted, embedded, failed | |
| error_message | text, nullable | |
| created_at / updated_at | timestamp | |

**file_chunks**
| Column | Type | Notes |
|---|---|---|
| id | int, PK | |
| file_id | int, FK → indexed_files (cascade delete) | |
| chunk_index | int | Order within the file |
| chroma_id | string(128), unique | Key into the Chroma collection |
| char_count | int | |
| created_at / updated_at | timestamp | |

### 5.2 Vector Store (Chroma)

- One persistent collection (`CHROMA_COLLECTION_NAME`, default `file_chunks`) under `CHROMA_PERSIST_DIR`.
- Each entry corresponds 1:1 with a `file_chunks` row via `chroma_id`.
- Deleting a file or reclassifying it as sensitive removes its chunk rows and their corresponding Chroma entries together, keeping the two stores consistent.

### 5.3 Data Retention / Deletion

- Removing a monitored folder cascades to delete all of its `indexed_files` and `file_chunks` rows and their Chroma embeddings.
- A scan that finds a file deleted from disk removes its record and embeddings the same way.
- Sensitive files are never persisted into the vector store under the default (skip) behavior; if a file is later reclassified as sensitive, existing embeddings for it are removed.
- Conversation history is not persisted server-side: each request carries its own `history`, held only in the frontend's in-memory chat state. Refreshing or closing the chat page discards the conversation; nothing conversational is written to the database.

---

## 6. Non-Functional Requirements

### 6.1 Security

- **NFR-SEC-1:** The system shall not index files identified as sensitive (credentials/keys) unless the user explicitly opts in for that scan. (See FR-SENS-3–8.)
- **NFR-SEC-2:** CORS origins accepted by the backend shall be explicitly configured (`BACKEND_CORS_ORIGINS`), not left open by default.
- **NFR-SEC-3:** Secrets (`SECRET_KEY`, database credentials) shall be supplied via environment configuration, never hardcoded, and the default placeholder value shall be changed before any non-local deployment.
- **NFR-SEC-4:** (Planned) Once authentication is implemented, all folder/file/search endpoints shall require a valid session/token.
- **NFR-SEC-5:** The AI answer feature shall send only the text of chunks already retrieved for the current query to the configured LLM provider (Groq Cloud) — no other indexed content, file paths, or system metadata shall be transmitted. This is inherent to the current implementation (`AnswerService`/`AnswerStreamService` only ever receive the retrieved `SearchResultItem` list), not a separate filter.
- **NFR-SEC-6:** The LLM provider API key (`GROQ_API_KEY`) shall be supplied via environment configuration only, consistent with NFR-SEC-3, and never logged or echoed back in API responses.
- **NFR-SEC-7:** The query-rewriting step shall send only the user's raw query text to the LLM provider — no indexed file content, file paths, or system metadata are part of that request (it happens before retrieval, so no file content exists yet to send).

### 6.2 Performance

- **NFR-PERF-1:** A folder scan estimate shall run as a read-only, checksum-free walk so it stays cheap enough to run synchronously ahead of a real scan.
- **NFR-PERF-2:** Estimated scan duration shall be surfaced to the user before committing to a full scan, based on configurable throughput assumptions (`ESTIMATE_FILES_PER_SECOND`, `ESTIMATE_BYTES_PER_SECOND`).
- **NFR-PERF-3:** Files at or above `LARGE_FILE_THRESHOLD_BYTES` (default 50 MB) shall be flagged to the user as likely to slow down processing.

### 6.3 Reliability / Data Integrity

- **NFR-REL-1:** Scans shall be idempotent with respect to unchanged files: an unchanged file (same mtime) is left untouched; same checksum with a changed mtime updates only the timestamp, without reprocessing.
- **NFR-REL-2:** Any folder-path access failure shall be surfaced with a specific, actionable error rather than a generic failure.

### 6.4 Usability

- **NFR-USE-1:** Before adding a folder or running a scan that would touch sensitive files, the user shall see a clear warning and an explicit choice, with the safe option (skip) as the default.
- **NFR-USE-2:** Scan/estimate results shall be presented with human-readable counts, durations, and byte sizes, not raw numbers alone.

### 6.5 Maintainability

- **NFR-MAINT-1:** Backend code shall follow the layered `endpoint -> service -> repository -> model` architecture with schemas decoupled from ORM models.
- **NFR-MAINT-2:** Database schema changes shall be made exclusively through Alembic migrations.

### 6.6 Portability

- **NFR-PORT-1:** The backend and frontend shall each run standalone (local dev) or together via Docker Compose, on Windows, Linux, or macOS hosts.

---

## 7. System Architecture Summary

```
Frontend (React/Vite)
  ├─ features/folders   → add/estimate/scan/remove folders, sensitive-file warnings
  ├─ features/files     → browse indexed files
  ├─ features/chat      → message bubbles, input, suggested questions, source citations
  ├─ features/onboarding→ first-run guidance
  ├─ hooks/useChat            → multi-turn conversation state + drives the /search/stream SSE connection
  ├─ hooks/useTheme           → light/dark theme toggle, persisted
  ├─ components/common/MarkdownContent → Markdown/GFM rendering + code block copy
  └─ pages/router       → Home, Folders, Chat, Files

Backend (FastAPI)
  ├─ api/v1/endpoints    → health, folders, files, search (HTTP layer only)
  ├─ services
  │   ├─ FolderService            → registration, validation, estimate
  │   ├─ FileScannerService        → disk <-> DB reconciliation
  │   ├─ IndexingPipeline           → extraction, chunking, embedding
  │   ├─ SearchService               → query rewriting + query embedding + vector search (retrieval)
  │   ├─ QueryRewriteService          → Groq-backed pre-retrieval query rewriting
  │   ├─ GroqClient                    → Groq Cloud HTTP transport (JSON mode + streaming)
  │   ├─ AnswerService                  → non-streaming grounded answer synthesis
  │   ├─ AnswerStreamService             → streaming grounded answer synthesis (SSE)
  │   ├─ SearchStreamService              → composes query rewriting + retrieval + streamed answer
  │   ├─ rag_context                       → shared grounding logic (context, confidence, history, fallback message)
  │   ├─ sensitive_file_detector            → credential/key file detection
  │   └─ folder_access_guard/path_guard      → filesystem validation
  ├─ repositories         → SQLAlchemy data access
  ├─ models                → monitored_folders, indexed_files, file_chunks
  └─ Chroma vector store    → persisted embeddings keyed by chroma_id
```

---

## 8. Future Work / Open Items

- Implement authentication and per-user data isolation (config scaffolding exists but is inactive).
- Expand the sensitive-file detection list (e.g. cloud provider credential file conventions, additional key formats) and consider making the pattern list configurable.
- Consider surfacing indexing failures (`status = failed`, `error_message`) more prominently in the UI.
- Evaluate direct file upload as an alternative ingestion path alongside folder monitoring.
- Add background/async scanning for very large folders instead of a synchronous scan request.
- Reconcile the two AI-answer confidence models (model-self-reported for non-streaming vs. retrieval-similarity-derived for streaming) into a single consistent measure, or clearly document the difference to end users.
- Support additional/alternate LLM providers behind the same `AnswerService`/`AnswerStreamService`/`QueryRewriteService` interfaces, since the current design is Groq-specific in `GroqClient` only.
- Evaluate whether query rewriting measurably improves retrieval quality in practice (vs. adding latency and an extra LLM call per query) and consider caching rewrites for repeated/similar queries.
- Consider condensing older conversation turns (summarization) instead of a hard cutoff at 12/20 messages, so very long conversations don't lose earlier context abruptly.

---

## 9. Approval / Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-14 | Initial SRS covering folder management, scanning/indexing, sensitive-file detection, search, and file browsing as currently implemented. |
| 1.1 | 2026-07-14 | Added AI-generated search answers (Groq): non-streaming JSON-mode answers and streamed (SSE) answers with live token rendering, cancel, retry, and copy in the UI. See §3.4a, §4.1.1, NFR-SEC-5/6. |
| 1.2 | 2026-07-14 | Replaced the single-query search page with a full multi-turn chat interface (Markdown rendering, code blocks, clickable citations, suggested questions, auto-scroll, dark mode); added conversation history support end-to-end; added Groq-backed query rewriting before retrieval. See §3.4a–d, §4.1, §4.1.1, §4.2, NFR-SEC-7. |
