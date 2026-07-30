# Software Requirements Specification (SRS)

## Reverse File Search

**Version:** 3.0
**Status:** Living document — reflects the current implemented feature set plus planned scope
**Date:** 2026-07-30

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for **Reverse File Search**, a multi-tenant, AI-powered application that lets a user register local folders for monitoring and then search across their contents using natural-language queries (semantic / "reverse" search), instead of searching by filename or exact keyword match. It also automatically classifies and structurally extracts information from indexed documents, lets the user converse with an AI grounded in that content, and offers on-demand document analysis (comparison, contract risk flagging, action-item extraction) — all behind full account authentication and organization-scoped access control.

It is intended for developers, testers, and reviewers who need a single reference for what the system does, how it is structured, and what constraints it operates under.

### 1.2 Scope

The system:

- Lets a user create an account (self-registration), verify their email, and sign in; every account belongs to exactly one **organization** at a time, which is the unit of data isolation.
- Automatically provisions a new, private organization for every self-registered user (except the very first user on a deployment, who becomes its platform Super Admin) — so a fresh signup never sees another user's folders or files unless explicitly invited into their organization.
- Supports inviting other people into an organization by email, with role selection, and lets organization admins manage members' roles and manage the organization's profile/settings.
- Enforces role-based access control (5 roles, 13 permission codes) on every folder/file/search/admin action, via permissions embedded in a signed access token.
- Lets a user register ("monitor") one or more local folders, scoped to their organization.
- Recursively scans each monitored folder, detects new/modified/deleted files, and reconciles an index of file metadata — either synchronously or as a background job with live progress over a WebSocket.
- Extracts text from supported file types (PDF, DOCX, TXT, Markdown, Excel, and images via OCR).
- Chunks and embeds extracted text using a sentence-embedding model, storing vectors in a persistent Chroma vector store, filtered by organization (and optionally folder/file) at query time.
- Detects and, by default, excludes potentially sensitive files (credentials, private keys, `.env` files, etc.) from indexing, with an explicit user override.
- Automatically classifies each indexed file into category tags (Invoice, Contract, Resume, Tax, Purchase Order, Medical Record, Salary Slip, Bank Statement, Receipt, Letter, or a custom category), shown as colored, icon-badged tags, filterable in the UI.
- Automatically extracts structured business/financial fields (invoice number, vendor, GST/PAN, amount, date, contact details, etc.) from indexed documents, best-effort.
- Generates an on-demand, structured document summary (executive summary, key points, dates, people, organizations, risks, action items) for any indexed file.
- Offers three additional on-demand document-analysis tools: **file comparison** (diff two indexed files), **contract risk analysis** (flag five common risk categories), and **action-item extraction** (person/task/deadline/priority, meeting-notes style).
- Answers natural-language queries by first rewriting the query for better retrieval (via an LLM), embedding the rewritten query, and retrieving the most semantically similar indexed chunks within the caller's organization — globally, or scoped to a single folder, or scoped to a single file's full content.
- Optionally synthesizes a grounded, cited natural-language answer from those chunks (via an LLM), across multi-turn conversations, with per-scope conversation memory.
- Suggests search queries as the user types: their own recent searches, the most popular searches, and AI-generated suggestions.
- Presents all of the above through a web UI: authentication pages, an organization dashboard/members/invitations/settings area, a personal profile and security/sessions area, folder management with live scan progress, indexed file browsing with tag filtering and per-file chat/summary/analysis tools, and a chat interface (global, folder-scoped, and file-scoped).

Out of scope for the current version (see §1.5 Assumptions/Constraints and §8 Future Work):

- Direct file upload as a primary ingestion path (the system indexes files in place from monitored folders).
- Remote/cloud storage backends (local filesystem only).
- Billing/subscription enforcement (an organization's `subscription_plan`/storage-quota fields exist in the schema but are not yet enforced anywhere).
- A superadmin-facing cross-organization admin console beyond the existing API-level bypass (see NFR-SEC-9).

### 1.3 Intended Audience

- Software engineers implementing or maintaining the system.
- QA engineers writing test plans against these requirements.
- Technical reviewers/stakeholders evaluating feature completeness.

### 1.4 Definitions, Acronyms, Abbreviations

| Term | Meaning |
|---|---|
| **Organization (Org, Tenant)** | The unit of data isolation. Every user belongs to exactly one organization at a time; folders, files, and search results never cross an organization boundary except for a superadmin/legacy token (see NFR-SEC-9). |
| **Platform-owner organization** | The organization created for the very first user ever registered on a deployment; that user becomes its Super Admin. |
| **Self-registration** | A user creating their own account via `POST /auth/register`, as opposed to being invited into an existing organization. |
| **Invitation** | A time-limited, single-use, email-addressed token that lets a specific person join a specific organization with a specific role, without going through self-registration. |
| **Role** | One of 5 named permission bundles (Super Admin, Organization Admin, Manager, Employee, Viewer) assigned to a user within an organization. |
| **Permission (code)** | One of 13 fine-grained capability flags (e.g. `folder.create`, `admin.roles`) checked by an endpoint before it executes. |
| **Access token** | A short-lived (15 min), RS256-signed JWT carrying the user's id, organization id, and permission/role claims; sent as a bearer token on every authenticated request. |
| **Refresh token** | A longer-lived (7 day) token used to obtain a new access token without re-entering credentials; delivered as an httpOnly cookie and in the response body, stored hashed server-side, and rotated on every use. |
| **Token family** | The set of refresh tokens produced by successive rotations from one original login; reusing an already-rotated (revoked) token in a family revokes the whole family as a session-hijack countermeasure. |
| **Session** | A server-side record (`user_sessions`) of one active token family — one per login — listable and individually revocable by the user. |
| **Monitored folder** | A local directory the user has registered for scanning/indexing, scoped to their organization. |
| **Scan** | A recursive walk of a monitored folder that reconciles the database's record of files with what's actually on disk. |
| **Indexing / Indexing pipeline** | Extracting text from a file, splitting it into chunks, embedding those chunks into the vector store, then best-effort tag classification and entity extraction. |
| **Chunk** | A bounded slice of a file's extracted text (default 500 words, 50-word overlap) that gets its own embedding. |
| **Embedding** | A numeric vector representation of text, produced by a sentence-embedding model, used for similarity search. |
| **Vector store** | Chroma — a persistent store of embeddings, queried for nearest neighbors to a query embedding, filterable by organization/folder/file metadata. |
| **Sensitive file** | A file whose name/extension strongly suggests it holds secrets (e.g. `.env`, `.pem`, `id_rsa`, `credentials.json`). |
| **Query rewriting** | An LLM pre-processing step that expands/clarifies the user's raw query before the vector search runs. |
| **Conversation / turn** | A single exchange in the chat interface; a conversation is an ordered sequence of turns. |
| **Scope (chat)** | What a conversation's retrieval is restricted to: unscoped (all indexed files in the org), folder-scoped, or file-scoped. |
| **Tag / classification** | A short category label automatically assigned to a file based on its content. |
| **Entities** | Structured business/financial fields automatically extracted from a file's text. |
| **SRS** | Software Requirements Specification (this document). |

### 1.5 Assumptions and Constraints

- The backend and the folders it monitors run on the same host/filesystem it has direct access to (or an accessible network share); the system does not fetch remote files over HTTP.
- PostgreSQL is the primary relational datastore for metadata; Chroma is the vector datastore for embeddings. Both must be reachable/writable by the backend process.
- An RS256 JWT keypair must exist on disk (`backend/keys/`, generated via `scripts/generate_jwt_keys.py`) before the API can issue or verify tokens.
- A reachable SMTP relay is required for account verification, password reset, and invitation emails to actually be delivered; the auth flows themselves never fail if SMTP is unreachable (best-effort send), but the user won't receive the email.
- OCR (image text extraction) requires a working Tesseract installation reachable via `PATH` or `TESSERACT_CMD`.
- All AI-backed features (query rewriting, AI answers, tag classification, entity extraction, summaries, AI-generated search suggestions, file comparison, contract risk analysis, action-item extraction) require a configured Groq Cloud API key; every one of them degrades gracefully to "unavailable" without it, and none of them affect core scanning/indexing/plain-search functionality.

---

## 2. Overall Description

### 2.1 Product Perspective

Reverse File Search is a self-contained two-tier web application:

- **Backend** — a FastAPI service exposing a REST API under `/api/v1` (plus one WebSocket endpoint for live scan progress), owning all business logic, persistence, authentication/authorization, and the embedding/search/classification/analysis pipeline.
- **Frontend** — a React single-page app that consumes the backend API and provides the user-facing workflows for account management, organization administration, folder management, scanning, browsing, tagging, searching/chatting, and document analysis.

```
┌─────────────┐   HTTP/JSON, SSE, WS   ┌──────────────┐      SQL      ┌────────────┐
│  Frontend   │ ─────────────────────► │   Backend    │ ────────────► │ PostgreSQL │
│  (React)    │ ◄───────────────────── │  (FastAPI)   │               │ (metadata) │
└─────────────┘                       └──────┬───────┘               └────────────┘
                                              │
                     embeddings, org filter    │      chat completions, email
                                              ▼                      ▼         ▼
                                        ┌────────────┐        ┌──────────────┐ ┌──────┐
                                        │   Chroma   │        │  Groq Cloud  │ │ SMTP │
                                        │ (vectors)  │        │ (LLM, opt.)  │ │(mail)│
                                        └────────────┘        └──────────────┘ └──────┘
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full service map and [`DFD.md`](DFD.md) for detailed data-flow diagrams.

### 2.2 Product Functions (Summary)

1. Register an account, verify email, sign in/out, recover a forgotten password, and manage active sessions.
2. Belong to an organization (own private one by default, or an invited shared one), with a role that determines what the user can do.
3. Invite people into an organization by email and manage their role/membership.
4. Register a folder to monitor, with upfront path validation and a scan estimate preview.
5. Scan a monitored folder — synchronously, or in the background with a live progress feed — to detect added/modified/deleted files.
6. Detect potentially sensitive files before indexing and let the user choose whether to skip or include them.
7. Extract text from supported file types and index it (chunk + embed), scoped to the caller's organization.
8. Automatically classify each indexed file into category tags and extract structured business fields, best-effort.
9. Generate an on-demand structured summary for any indexed file.
10. Compare two indexed files, flag contract risk categories, and extract action items from a file, on demand.
11. List and inspect indexed files, their status, and their tags, with folder/tag filtering.
12. Chat with an AI grounded in indexed file content — globally, scoped to one folder, or scoped to one file — across multiple turns, with the underlying query rewritten before each unscoped/folder-scoped retrieval for better recall.
13. Suggest searches as the user types (recent, popular, AI-generated).
14. Remove a monitored folder (and its indexed data).

### 2.3 User Classes and Characteristics

| User class | Description |
|---|---|
| **End user (any role)** | Registers/joins an organization, and — depending on role — registers folders, runs scans, browses/filters files, chats with content, and uses document-analysis tools. No special technical knowledge required beyond providing a folder path. |
| **Organization Admin** | Manages the organization's profile/settings, invites/removes members, changes member roles; has full folder/file/search/chat access within their org. This is the default role for anyone who self-registers a new organization. |
| **Manager** | Can register/scan folders and use all file/search/chat features, but cannot delete folders or perform admin actions. |
| **Employee** | Can read folders, read/download/summarize files, search, and chat, but cannot create/delete/scan folders. |
| **Viewer** | Read-only: can see folders and files and run searches, but cannot download files, view summaries/entities, or use chat. |
| **Super Admin** | Platform-level role held only by the very first user registered on a deployment; bypasses all permission checks and organization filtering. |
| **Operator/Administrator** | Deploys and configures the backend/frontend (environment variables, database, storage paths, SMTP, Groq API key, JWT keypair), manages the Docker Compose stack. |

See §3.16 (Roles & Permissions) for the full permission matrix.

### 2.4 Operating Environment

- **Backend:** Python 3.12+/3.13, FastAPI/Uvicorn, PostgreSQL 14+, ChromaDB persistent store, an RS256 JWT keypair, optional Tesseract OCR binary, optional Groq Cloud API access, optional SMTP relay. Runs on Windows, Linux, or macOS; Docker image provided (`docker/backend.Dockerfile`).
- **Frontend:** Node.js 20+ for development/build; the built static assets are served independently of the backend (or via `docker/frontend.Dockerfile`). Runs in any modern evergreen browser.
- **Deployment:** `docker-compose.yml` at the repo root orchestrates Postgres + backend + frontend together for local/integrated runs.

### 2.5 Design and Implementation Constraints

- Layered backend architecture is mandatory: `endpoint -> service -> repository -> model`, with Pydantic schemas decoupled from ORM models.
- Every folder/file/search endpoint accepts the caller's organization id (derived from their access token, never from client input) and filters/stamps all reads and writes by it.
- Only the file types in `SUPPORTED_EXTENSIONS` (`app/services/file_type_detector.py`) are eligible for indexing: `.pdf`, `.docx`, `.txt`, `.md`/`.markdown`, `.png`/`.jpg`/`.jpeg`/`.bmp`/`.tiff`/`.tif`, `.xlsx`/`.xls`.
- Certain directory names are always skipped during a scan (`SCAN_IGNORE_DIR_NAMES`): `__pycache__`, `node_modules`, `.git`, `.venv`, `venv`, `.idea`, `.vscode`, `System Volume Information`, `$RECYCLE.BIN`, `.Trash`.
- Hidden/system files (dotfiles, OS hidden/system attribute) are excluded from indexing.
- Sensitive-looking files are excluded from indexing by default (see §3.5).
- Database schema changes must go through Alembic migrations.
- All Groq-backed enrichment (tagging, entity extraction) runs after a file successfully embeds and can never turn a successfully-indexed file into a failed one, even if it errors.
- Passwords are hashed with Argon2id; refresh tokens are stored only as SHA-256 hashes, never in plaintext.

### 2.6 Assumptions/Dependencies

See §1.5. Additionally, the embedding model (`all-MiniLM-L6-v2` by default) is downloaded/cached by `sentence-transformers` on first use and must be available (network access on first run, or a pre-populated model cache).

---

## 3. Functional Requirements

Each requirement is numbered `FR-<area>-<n>` and marked with an implementation status.

### 3.1 Registration & Account Verification

| ID | Requirement | Status |
|---|---|---|
| FR-REG-1 | The system shall allow a visitor to self-register an account with email, password, and optional full name (`POST /auth/register`), rate-limited to 3 requests/minute per client. | Implemented |
| FR-REG-2 | The system shall reject registration with an email that already has an account (409). | Implemented |
| FR-REG-3 | The very first user ever registered on a deployment shall become that deployment's Super Admin, owning a newly-created "platform-owner" organization. | Implemented |
| FR-REG-4 | Every self-registered user other than the first shall be provisioned with their own new, separate organization and become its Organization Admin/owner — never automatically joining another user's organization. | Implemented |
| FR-REG-5 | A newly-registered account shall be unverified until the user follows a time-limited (24h) email verification link (`POST /auth/verify-email`); the system shall send this link via a best-effort email that never blocks or fails registration if the mail send itself fails. | Implemented |
| FR-REG-6 | The system shall allow requesting the verification email again (`POST /auth/resend-verification`), responding identically whether or not the email is known or already verified (enumeration-safe). | Implemented |

### 3.2 Login, Sessions & Token Lifecycle

| ID | Requirement | Status |
|---|---|---|
| FR-AUTH-1 | The system shall authenticate a user by email and password (`POST /auth/login`, rate-limited 5/minute), rejecting unverified accounts and locked accounts with distinct error responses (401 / 423). | Implemented |
| FR-AUTH-2 | After 5 consecutive failed login attempts, the system shall lock the account for 15 minutes, rejecting further attempts (423) even with the correct password until the lock expires. | Implemented |
| FR-AUTH-3 | On successful login, the system shall issue a short-lived (15 min) RS256-signed access token carrying the user's id, organization id, permissions, and roles, plus a longer-lived (7 day) refresh token. | Implemented |
| FR-AUTH-4 | The refresh token shall be delivered both as an httpOnly, `SameSite=Lax` cookie (scoped to `/api/v1/auth`, `Secure` in production) and in the JSON response body, and shall be stored server-side only as a salted hash. | Implemented |
| FR-AUTH-5 | The system shall support obtaining a new access/refresh token pair from a valid refresh token (`POST /auth/refresh`), rotating the refresh token on every use; cookie-based refresh shall additionally require an `X-Requested-With: XMLHttpRequest` header (403 if absent) as CSRF mitigation. | Implemented |
| FR-AUTH-6 | Reuse of an already-rotated (previously superseded) refresh token shall revoke every token descended from the same original login ("family") and terminate its session, rejecting the request (401). | Implemented |
| FR-AUTH-7 | The system shall allow explicit logout (`POST /auth/logout`), revoking the current refresh-token family and its session. | Implemented |
| FR-AUTH-8 | The system shall record one session per login (ip address, user agent, created/revoked timestamps), listable (`GET /me/sessions`) and individually revocable (`DELETE /me/sessions/{id}`) by the account owner. | Implemented |
| FR-AUTH-9 | On every login, the system shall send a best-effort security notification email describing the ip address and device/browser used. | Implemented |

### 3.3 Password Management

| ID | Requirement | Status |
|---|---|---|
| FR-PWD-1 | The system shall let an authenticated user change their password given their current password (`POST /auth/change-password`), rejecting the request (401) if the current password is wrong. | Implemented |
| FR-PWD-2 | The system shall let an unauthenticated user request a password-reset email (`POST /auth/forgot-password`, rate-limited 3/minute), responding identically regardless of whether the email is known (enumeration-safe). | Implemented |
| FR-PWD-3 | A password-reset link shall expire after 1 hour and be single-use (`POST /auth/reset-password`). | Implemented |
| FR-PWD-4 | Successfully resetting a password shall revoke all of that user's active sessions and refresh-token families, forcing re-authentication everywhere. | Implemented |

### 3.4 Organizations & Multi-Tenancy

| ID | Requirement | Status |
|---|---|---|
| FR-ORG-1 | Every user shall belong to exactly one organization at a time; every monitored folder and indexed file shall be permanently associated with the organization that created it. | Implemented |
| FR-ORG-2 | Folder/file listings, folder/file actions, and search/chat retrieval shall be filtered to the caller's own organization; no ordinary user's request shall return another organization's folders, files, or search results. | Implemented |
| FR-ORG-3 | The system shall let an authorized member (`admin.settings` permission) view and update their organization's profile: name, logo, website, contact email/phone, country, timezone, industry (`GET`/`PATCH /organizations/{id}`). | Implemented |
| FR-ORG-4 | The system shall let a user with membership in more than one organization (or a superadmin) switch their active organization context (`POST /organizations/{id}/switch`), re-issuing a token pair scoped to the new organization. | Implemented |

### 3.5 Invitations & Membership Management

| ID | Requirement | Status |
|---|---|---|
| FR-INV-1 | The system shall let an authorized member (`admin.users` permission) invite a person to their organization by email with a chosen role (`POST /organizations/{id}/invite`), sending an invitation email with a single-use token. | Implemented |
| FR-INV-2 | The system shall reject inviting the same email to the same organization while a prior invitation to them is still pending. | Implemented |
| FR-INV-3 | The system shall reject inviting someone with the "Super Admin" role. | Implemented |
| FR-INV-4 | The system shall let an authorized member list, resend, or revoke pending invitations for their organization. | Implemented |
| FR-INV-5 | The system shall let anyone holding a valid, unexpired, pending invitation token accept it (`POST /invitations/accept`), creating a new account (auto-verified) if none exists for that email, or attaching an existing orgless account, assigning the invited role, and signing the user in immediately. | Implemented |
| FR-INV-6 | Accepting an invitation shall mark it accepted and send the new member a welcome/"joined" email. | Implemented |
| FR-MEM-1 | The system shall let an authorized member (`admin.users`) list an organization's members. | Implemented |
| FR-MEM-2 | The system shall let an authorized member (`admin.roles`) change another member's role, and (`admin.users`) remove or suspend another member. | Implemented |
| FR-MEM-3 | The system shall reject any role change, removal, or suspension targeted at a member whose membership status is "Owner" (the founding member of that organization). | Implemented |

### 3.6 Roles & Permissions (RBAC)

| ID | Requirement | Status |
|---|---|---|
| FR-RBAC-1 | The system shall define exactly 5 roles (Super Admin, Organization Admin, Manager, Employee, Viewer) and 13 permission codes, per the matrix in §3.16 below. | Implemented |
| FR-RBAC-2 | Every folder/file/search/admin endpoint shall require a specific permission code, checked against the permissions embedded in the caller's access token at the time it was issued. | Implemented |
| FR-RBAC-3 | A user flagged `is_superadmin` shall bypass all permission checks and all organization-scoping filters. | Implemented |
| FR-RBAC-4 | A role change shall take effect only on the affected user's next login/token refresh, since permissions are embedded in the access token at issuance, not re-checked live against the database on every request. | Implemented |

### 3.7 Folder Management

| ID | Requirement | Status |
|---|---|---|
| FR-FOLD-1 | The system shall allow a user with `folder.create` permission to register a folder for monitoring, scoped to their organization, by providing an absolute filesystem path. | Implemented |
| FR-FOLD-2 | The system shall validate a folder path before registration and reject it with a specific, descriptive error for: missing path, non-directory path, permission denied, path locked by another process, unreachable network location, or an overly broad path (e.g. a drive root). | Implemented |
| FR-FOLD-3 | The system shall reject registering a folder path that is already monitored within the same organization. | Implemented |
| FR-FOLD-4 | The system shall provide a scan estimate (`POST /folders/estimate`) for a candidate path without persisting anything, returning: total files found, supported vs. unsupported file counts, estimated processing time, estimated storage size, count of large files (≥ configurable threshold), and count/sample of detected sensitive files. | Implemented |
| FR-FOLD-5 | The system shall list all folders monitored within the caller's organization (`folder.read` permission). | Implemented |
| FR-FOLD-6 | The system shall allow a user with `folder.delete` permission to remove a monitored folder, which also removes all of that folder's indexed file records and associated vector-store embeddings. | Implemented |

### 3.8 Scanning and Indexing

| ID | Requirement | Status |
|---|---|---|
| FR-SCAN-1 | The system shall recursively scan a monitored folder's contents, skipping configured ignore-directories and hidden/system files. | Implemented |
| FR-SCAN-2 | The system shall detect and record newly discovered supported files as pending indexing. | Implemented |
| FR-SCAN-3 | The system shall detect files whose modification time has changed since the last scan and re-check their checksum; if the checksum differs, the system shall re-extract/re-embed the file's content and delete its previous chunks/embeddings. If the checksum is unchanged, only the recorded modification time is updated (no re-processing). | Implemented |
| FR-SCAN-4 | The system shall detect files that existed in the index but are no longer present on disk and remove their records and embeddings. | Implemented |
| FR-SCAN-5 | After a scan, the system shall process all pending files through the indexing pipeline: extract text, split it into overlapping word-count-bounded chunks, and embed each chunk into the vector store, tagged with the owning organization. | Implemented |
| FR-SCAN-6 | The system shall report scan results as counts of files added, modified, deleted, skipped (unchanged), and skipped-as-sensitive. | Implemented |
| FR-SCAN-7 | The system shall report indexing results as counts of files extracted, embedded, and failed. | Implemented |
| FR-SCAN-8 | Only files with a supported extension shall be eligible for text extraction and embedding; unsupported files are counted but never processed. | Implemented |
| FR-SCAN-9 | The system shall support starting a scan as a background operation (`POST /folders/{id}/scan/start`) that returns immediately with a scan identifier, requiring `folder.scan` permission. | Implemented |
| FR-SCAN-10 | The system shall provide a live progress feed for a background scan over a WebSocket (`/ws/scan/{scan_id}`), emitting per-file/per-stage progress events (stage, current file, processed/remaining counts, elapsed time, estimated remaining time) followed by exactly one terminal summary or error event. | Implemented |
| FR-SCAN-11 | The frontend shall display background scan progress as a staged checklist with a progress bar, live stats, and — on completion — a success summary and a list of any per-file failures with their error messages. | Implemented |

### 3.9 Sensitive File Detection

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

### 3.10 Automatic Document Classification (Tags)

| ID | Requirement | Status |
|---|---|---|
| FR-TAG-1 | After a file successfully embeds, the system shall best-effort classify its content into up to 5 short category tags via an LLM, preferring one of: Invoice, Contract, Resume, Tax, Purchase Order, Medical Record, Salary Slip, Bank Statement, Receipt, Letter — or a concise custom category if none fit. | Implemented |
| FR-TAG-2 | Tag generation shall never affect a file's indexing status — a failure (provider unavailable, unreachable, malformed response) is logged and results in no tags for that file, never a failed index. | Implemented |
| FR-TAG-3 | Re-indexing a file (e.g. after a content change) shall regenerate its tags, replacing the previous set. | Implemented |
| FR-TAG-4 | The system shall provide endpoints to retrieve a single file's tags, and to bulk-retrieve tags for every tagged file (optionally scoped to a folder), to avoid one request per file in list views. | Implemented |
| FR-TAG-5 | The system shall support filtering the indexed-files list by exact tag (case-insensitive). | Implemented |
| FR-TAG-6 | The frontend shall render each tag as a colored, icon-labeled badge — a stable color and icon per well-known category, with a deterministic fallback for custom categories — in both the files table and a file's detail view. | Implemented |
| FR-TAG-7 | The frontend Files page shall provide a tag filter control, populated from the tags actually present, that narrows the file list to that category. | Implemented |

### 3.11 Structured Entity Extraction

| ID | Requirement | Status |
|---|---|---|
| FR-ENT-1 | After a file successfully embeds, the system shall best-effort extract structured business/financial fields from its text via an LLM: invoice number, vendor, customer, GST, PAN, amount, date, email, phone, address, bank, PO number, contract number. | Implemented |
| FR-ENT-2 | Extraction shall never guess or fabricate a value — a field not explicitly present in the document text shall be `null`. | Implemented |
| FR-ENT-3 | Entity extraction shall never affect a file's indexing status, following the same failure-isolation rule as FR-TAG-2. | Implemented |
| FR-ENT-4 | The system shall provide an endpoint to retrieve a single file's extracted entities, requiring `file.entities` permission. | Implemented |

### 3.12 On-Demand Document Summaries

| ID | Requirement | Status |
|---|---|---|
| FR-SUM-1 | The system shall generate, on explicit request (`file.summary` permission), a structured summary of an indexed file: an executive summary, key points, important dates (each described in context), people, organizations, risks, and action items — grounded strictly in the file's own extracted text. | Implemented |
| FR-SUM-2 | Summary generation shall re-extract the file's text at request time (not reuse indexing-time text), and shall fail with a specific error if the file's text can't be extracted or is empty, if no LLM provider is configured, or if the provider call itself fails. | Implemented |
| FR-SUM-3 | A generated summary shall be persisted and returned by a subsequent read without regenerating, until the user explicitly requests generation again. | Implemented |
| FR-SUM-4 | The frontend file detail view shall offer a way to view an existing summary or trigger generation of one. | Implemented |

### 3.13 Document Comparison, Contract Risk & Action Items

| ID | Requirement | Status |
|---|---|---|
| FR-CMP-1 | The system shall let a user (`file.read` permission) compare two indexed files within their own organization (`POST /files/compare`), returning a natural-language summary of differences, added clauses, removed clauses, and financial changes, grounded in both files' extracted text. | Implemented |
| FR-CMP-2 | Comparison shall fail with a specific error if either file cannot be found in the caller's organization (404), no LLM provider is configured (503), either file's text cannot be extracted (422), or the LLM call fails (502). | Implemented |
| FR-RISK-1 | The system shall let a user (`file.read` permission) request a contract risk analysis of a single indexed file (`POST /files/{id}/contract-risks`), returning exactly five fixed risk categories — Missing Signature, Unlimited Liability, Auto-Renewal, Late Fees, Termination Clause — each flagged present/absent with a plain-language explanation. | Implemented |
| FR-RISK-2 | Any risk category the underlying model does not address in its response shall be backfilled as not present, with an explanation stating it was not addressed in the document, rather than omitted from the result. | Implemented |
| FR-ACT-1 | The system shall let a user (`file.read` permission) extract action items from a single indexed file (`POST /files/{id}/action-items`), returning a list of `{person, task, deadline, priority}` entries suited to meeting-notes-style documents. | Implemented |
| FR-ACT-2 | An action item with no discernible task text shall be dropped from the result; an item missing or malformed priority shall default to "Medium" rather than failing the whole request. | Implemented |
| FR-ACT-3 | Comparison, contract risk analysis, and action-item extraction results shall not be persisted — each request recomputes the result from the file(s)' current text. | Implemented |

### 3.14 Search

| ID | Requirement | Status |
|---|---|---|
| FR-SRCH-1 | The system shall accept a free-text natural-language query and an optional result limit (`top_k`, default 10), requiring `search.execute` permission. | Implemented |
| FR-SRCH-2 | The system shall embed the query (after query rewriting, see §3.15) using the same embedding model used for indexing, and perform a similarity search against the vector store, filtered to the caller's organization. | Implemented |
| FR-SRCH-3 | The system shall return ranked results, each including the source file's ID and filename, the matching chunk's text, and a similarity score. | Implemented |
| FR-SRCH-4 | The frontend shall provide a chat interface where a user enters a query and views the ranked results and any generated answer (see §3.17). | Implemented |
| FR-SRCH-5 | The system shall support restricting retrieval to files within a single monitored folder (`folder_id`), applied as a metadata filter on the vector search, in addition to the organization filter. | Implemented |
| FR-SRCH-6 | The system shall support restricting retrieval to a single file's own content (`file_id`), returning that file's full chunk set in document order rather than a similarity-ranked subset, bounded by a maximum chunk/character cap. `file_id` scoping takes precedence over `folder_id` if both are supplied. | Implemented |

### 3.15 Query Rewriting

| ID | Requirement | Status |
|---|---|---|
| FR-QR-1 | Before embedding, the system shall optionally rewrite the user's raw query via an LLM (Groq) to improve retrieval accuracy — e.g. expanding acronyms or adding likely context terms (example: "GST" → "GST invoices issued during financial year"). | Implemented |
| FR-QR-2 | The rewrite step shall be instructed to preserve the original query's intent and shall not introduce new topics, assumptions, or specifics not supported by the original query. | Implemented |
| FR-QR-3 | The system shall support disabling query rewriting per-request (`rewrite_query: false`); when disabled, or when no LLM provider is configured, or when the rewrite call fails for any reason, retrieval shall fall back to embedding the original, unmodified query — a failed or disabled rewrite shall never block search. | Implemented |
| FR-QR-4 | The system shall return the query text actually used for retrieval (the rewritten query, or the original if unchanged) to the caller: as `rewritten_query` in the non-streaming response, and as a dedicated `query` event sent before retrieval results in the streaming response. | Implemented |
| FR-QR-5 | The answer-generation step shall reference the user's original query text, not the rewritten form, when framing its response — rewriting affects retrieval only, not the language of the answer. | Implemented |
| FR-QR-6 | Query rewriting shall not apply to file-scoped retrieval (FR-SRCH-6), since that path does not perform an embedding search. | Implemented |

### 3.16 Roles & Permissions Matrix (Reference)

| Permission code | Super Admin | Organization Admin | Manager | Employee | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| `folder.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `folder.create` | ✅ | ✅ | ✅ | – | – |
| `folder.delete` | ✅ | ✅ | – | – | – |
| `folder.scan` | ✅ | ✅ | ✅ | – | – |
| `file.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `file.download` | ✅ | ✅ | ✅ | ✅ | – |
| `file.summary` | ✅ | ✅ | ✅ | ✅ | – |
| `file.entities` | ✅ | ✅ | ✅ | ✅ | – |
| `search.execute` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `chat.execute` | ✅ | ✅ | ✅ | ✅ | – |
| `admin.users` | ✅ | ✅ | – | – | – |
| `admin.roles` | ✅ | ✅ | – | – | – |
| `admin.settings` | ✅ | ✅ | – | – | – |

Super Admin additionally bypasses all organization-scoping filters (§ NFR-SEC-9), not just permission checks.

### 3.17 Conversation History & Scoping

| ID | Requirement | Status |
|---|---|---|
| FR-CHAT-1 | The system shall support multi-turn conversations: a request may include prior turns as `history: [{role, content}, ...]`, appended to the messages sent to the answer-generating LLM so it can resolve conversational follow-ups. | Implemented |
| FR-CHAT-2 | Conversation history shall not affect retrieval — each turn's vector search shall embed only that turn's (rewritten) query, never prior conversation content. | Implemented |
| FR-CHAT-3 | The system shall cap the number of history messages included in the LLM prompt (12 server-side, regardless of what the client sends) to bound prompt size and cost. | Implemented |
| FR-CHAT-4 | The frontend shall maintain the full conversation as an ordered list of turns, sending only the most recent messages (last 20) as history, and excluding any assistant turn that is in progress, errored, or was cancelled from that history. | Implemented |
| FR-CHAT-5 | The frontend shall allow retrying an individual assistant turn, regenerating it using the conversation history up to (but not including) that turn. | Implemented |
| FR-CHAT-6 | The frontend shall support a folder-scoped chat, reachable from a folder's row action, which restricts retrieval to that folder (FR-SRCH-5), displays a persistent indicator of the active scope, and offers a way to exit back to the unscoped conversation. | Implemented |
| FR-CHAT-7 | The frontend shall support a file-scoped chat, reachable from a file's detail view, which restricts retrieval to that file's own content (FR-SRCH-6). | Implemented |
| FR-CHAT-8 | Conversation memory shall be isolated per scope: switching between the unscoped conversation, a different folder's scoped conversation, or a different file's scoped conversation shall never carry over turns from a different scope. | Implemented |

### 3.18 AI-Generated Answers

| ID | Requirement | Status |
|---|---|---|
| FR-AI-1 | The system shall optionally synthesize a natural-language answer from the retrieved chunks using an LLM (Groq Cloud), returned alongside the normal ranked results. | Implemented |
| FR-AI-2 | The system shall support this via two modes: a non-streaming JSON response (`POST /search/` with `generate_answer: true`) and a streamed response (`POST /search/stream`, Server-Sent Events, always generates an answer). | Implemented |
| FR-AI-3 | The model shall be instructed to answer using only the retrieved excerpts and shall never be presented as having access to outside knowledge. | Implemented |
| FR-AI-4 | Answer sources shall be derived deterministically from the filenames of the retrieved chunks, never from the model's own output, so citations cannot be hallucinated. | Implemented |
| FR-AI-5 | If the retrieved context does not support an answer, the system shall return the exact message "I couldn't find enough information." instead of an invented answer, in both the non-streaming and streaming modes. | Implemented |
| FR-AI-6 | The non-streaming mode shall return a confidence score self-reported by the model (constrained to [0, 1]) alongside an explicit sufficiency flag used to decide whether to return the model's answer or the insufficient-context fallback. | Implemented |
| FR-AI-7 | If no AI provider is configured, or the provider is unreachable, normal search results shall still be returned; only the AI answer shall be omitted (non-streaming) or reported via a distinct error event (streaming). | Implemented |
| FR-AI-8 | The streaming endpoint shall emit, over a single connection, in order: the query actually used for retrieval, the retrieved results, source/confidence metadata (derived from retrieval similarity, since no model output exists yet to self-report from), the answer text as a sequence of token events, then a completion or error event. | Implemented |
| FR-AI-9 | The frontend shall render streamed answer tokens live as they arrive, with a typing indicator shown before the first token. | Implemented |
| FR-AI-10 | The frontend shall allow the user to cancel an in-progress AI answer generation; the in-flight request shall be aborted and the underlying server-side connection to the LLM provider shall be closed. | Implemented |
| FR-AI-11 | The frontend shall allow the user to retry generation after completion, cancellation, or an error, re-running the same query. | Implemented |
| FR-AI-12 | The frontend shall allow the user to copy the generated answer text to the clipboard at any point once any text has been generated. | Implemented |

### 3.19 Search Suggestions

| ID | Requirement | Status |
|---|---|---|
| FR-SUGG-1 | The system shall log every search query submitted through either search endpoint, for the sole purpose of deriving suggestions. | Implemented |
| FR-SUGG-2 | The system shall provide an endpoint returning, for a given partial input: the user's most recent distinct past queries, the most frequent past queries, and AI-generated suggestions — each optionally filtered by the partial input as a prefix. | Implemented |
| FR-SUGG-3 | AI-generated suggestions shall adapt to whether the user has typed anything yet: generic example queries when the input is empty, completions/related queries when it is not. | Implemented |
| FR-SUGG-4 | AI-generated suggestions shall be best-effort — an empty list if no LLM provider is configured or the call fails — and shall never block or delay the recent/popular lists. | Implemented |
| FR-SUGG-5 | The frontend search box shall present suggestions in three labeled sections (Recent, Popular, AI-generated) and update them live (debounced) as the user types. | Implemented |
| FR-SUGG-6 | Selecting a suggestion shall submit it as the search immediately. | Implemented |

### 3.20 Chat Interface

| ID | Requirement | Status |
|---|---|---|
| FR-CHATUI-1 | The frontend shall present a single conversational chat interface (not a per-query toggle) as the primary way to search and get answers; every message is sent through the streaming endpoint. | Implemented |
| FR-CHATUI-2 | Assistant responses shall be rendered as Markdown, including GitHub-Flavored Markdown elements (tables, lists, etc.). | Implemented |
| FR-CHATUI-3 | Fenced code blocks within an assistant response shall be visually distinguished (monospace, bordered, labeled with the fence's declared language when present) and shall offer their own copy-to-clipboard control independent of the whole-message copy action. | Implemented |
| FR-CHATUI-4 | Cited source filenames shall be rendered as clickable elements; selecting one that corresponds to a retrieved file shall open that file's detail view. | Implemented |
| FR-CHATUI-5 | When a conversation is empty, the frontend shall present a set of suggested starter questions the user can select instead of typing, tailored to the active scope (unscoped, folder, or file). | Implemented |
| FR-CHATUI-6 | The message list shall automatically scroll to show new content as it streams in, unless the user has manually scrolled away from the bottom, in which case automatic scrolling shall pause until the user returns to the bottom. | Implemented |
| FR-CHATUI-7 | The frontend shall provide a light/dark theme toggle, persisted across sessions, defaulting to the operating system's preference on first visit. | Implemented |
| FR-CHATUI-8 | The chat layout shall be usable on both desktop and narrow (mobile-width) viewports. | Implemented |

### 3.21 Indexed File Browsing

| ID | Requirement | Status |
|---|---|---|
| FR-FILE-1 | The system shall list indexed files within the caller's organization, optionally filtered by monitored folder and/or by category tag. | Implemented |
| FR-FILE-2 | The system shall provide detail retrieval for a single indexed file by ID, returning 404 if not found (or not in the caller's organization). | Implemented |
| FR-FILE-3 | The system shall serve a file's original content inline (for viewing in-browser), returning 404 if the record or the underlying file is missing, requiring `file.download` permission. | Implemented |
| FR-FILE-4 | The frontend shall provide a files page listing indexed files (with search, folder filter, tag filter, sort, and pagination) and a detail view showing an individual file's metadata, indexing status, tags, and access to summary, comparison, contract risk analysis, action items, and per-file chat. | Implemented |

### 3.22 Health / Operations

| ID | Requirement | Status |
|---|---|---|
| FR-OPS-1 | The system shall expose a health-check endpoint (`GET /health`) suitable for readiness/liveness probes. | Implemented |

---

## 4. External Interface Requirements

### 4.1 REST & WebSocket API (Backend)

See [`API_REFERENCE.md`](API_REFERENCE.md) for the complete, current endpoint-by-endpoint reference (request/response shapes, status codes, SSE/WS event protocols). Summary of resources:

| Resource | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/verify-email`, `POST /auth/resend-verification`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password` |
| Me | `GET/PATCH /me`, `GET /me/sessions`, `DELETE /me/sessions/{id}` |
| Organizations | `GET/PATCH /organizations/{id}`, `POST /organizations/{id}/switch`, `GET /organizations/{id}/members`, `POST /organizations/{id}/invite`, `GET /organizations/{id}/invitations`, `POST /organizations/{id}/invitations/{id}/resend`, `DELETE /organizations/{id}/invitations/{id}` |
| Members | `PATCH /members/{id}/role`, `DELETE /members/{id}`, `POST /members/{id}/suspend` |
| Invitations | `POST /invitations/accept` |
| Folders | `GET/POST /folders/`, `POST /folders/estimate`, `DELETE /folders/{id}`, `POST /folders/{id}/scan`, `POST /folders/{id}/scan/start` |
| Files | `GET /files/`, `GET /files/tags`, `GET /files/{id}`, `GET /files/{id}/content`, `GET /files/{id}/tags`, `GET /files/{id}/entities`, `GET/POST /files/{id}/summary`, `POST /files/compare`, `POST /files/{id}/contract-risks`, `POST /files/{id}/action-items` |
| Search | `POST /search/`, `POST /search/stream`, `GET /search/suggestions` |
| WebSocket | `WS /ws/scan/{scan_id}` |

### 4.2 Web UI (Frontend)

| Route | Purpose |
|---|---|
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/invitations/accept` | Public authentication/account flows |
| `/` | Overview dashboard (folder/file/status counts, onboarding guidance) |
| `/folders` | Register, preview, scan (sync or background-with-progress), remove monitored folders; sensitive-file warning dialogs; per-folder Chat |
| `/search` | Chat interface: unscoped or folder-scoped (`?folderId=`) multi-turn conversation, with search-box autocomplete, Markdown rendering, code blocks, clickable citations, suggested questions, streamed responses, per-message cancel/retry/copy, and a light/dark theme toggle (nav label "Chat") |
| `/files` | Browse indexed files (search/folder/tag filters, sort, pagination); detail view with tags, on-demand summary, comparison, contract risk analysis, action items, and per-file Chat |
| `/profile` | View/edit personal profile |
| `/security`, `/security/sessions` | Change password, view/revoke active sessions |
| `/organization/dashboard`, `/organization/members`, `/organization/invitations`, `/organization/settings` | Organization overview, member list/role management, pending invitations, organization profile settings |

### 4.3 Configuration Interfaces

Both tiers are configured via `.env` files (`backend/.env.example`; the frontend reads `VITE_API_BASE_URL` and similar `VITE_*` variables). See [`INSTALLATION.md`](INSTALLATION.md) and `app/core/config.py` for the full backend variable list.

---

## 5. Data Requirements

See [`ARCHITECTURE.md §4`](ARCHITECTURE.md#4-data-model) and [`DFD.md`](DFD.md) for the full data-flow picture. Current relational schema (19 tables):

| Table | Purpose |
|---|---|
| `users` | Account credentials, verification/lockout state, superadmin/platform-owner flags, organization FK |
| `organizations` | Tenant profile: name, slug, contact info, plan, storage quota, platform-owner flag |
| `organization_users` | Membership: user↔org with role, status (invited/joined/suspended/owner), primary flag |
| `organization_invitations` | Pending/resolved email invitations to join an org with a role, single-use token |
| `roles` | Role definitions (Super Admin, Organization Admin, Manager, Employee, Viewer) |
| `permissions` | Permission code catalog (13 codes) |
| `user_roles` | User↔role assignment, per organization |
| `refresh_tokens` | Hashed refresh tokens with rotation family id, revocation/replacement tracking |
| `email_verifications` | Hashed, expiring email-verification tokens |
| `password_reset_tokens` | Hashed, expiring password-reset tokens |
| `user_sessions` | One row per refresh-token rotation family; active/revoked session tracking |
| `login_history` | Every login attempt (success/failure + reason, ip, user agent) |
| `audit_logs` | Immutable audit trail of security/business actions |
| `monitored_folders` | Registered/monitored folder paths, organization-scoped |
| `indexed_files` | Core file record: path, checksum, size, type, index status, OCR-corrected text, organization-scoped |
| `file_chunks` | Text chunks of an indexed file used for embedding/RAG retrieval |
| `file_tags` | Tags (including sensitive-file flags) attached to a file |
| `document_entities` | Extracted named entities/structured fields per file |
| `file_summaries` | AI-generated summary per indexed file (cached) |
| `search_query_logs` | Logged search/chat queries (for recent/popular suggestions) |

Embeddings themselves live in a Chroma persistent collection (`storage/chroma`), keyed by `chroma_id` and filterable by `organization_id`/`folder_id`/`file_id` metadata. File comparison, contract risk analysis, and action-item extraction use Pydantic schemas only — no dedicated tables (see FR-CMP/FR-RISK/FR-ACT — results are not persisted).

### 5.1 Data Retention / Deletion

- Removing a monitored folder cascades to delete all of its `indexed_files`, `file_chunks`, `document_entities`, `file_summaries`, and `file_tags` rows, and their Chroma embeddings.
- A scan that finds a file deleted from disk removes its record and embeddings the same way.
- Sensitive files are never persisted into the vector store under the default (skip) behavior; if a file is later reclassified as sensitive, existing embeddings for it are removed.
- Re-indexing a file (content changed) replaces its chunks, tags, and re-runs entity extraction; an existing summary is left as-is until explicitly regenerated.
- Conversation history is not persisted server-side: each request carries its own `history`, held only in the frontend's in-memory chat state per scope. Refreshing or closing the chat page, or switching scope, discards that conversation.
- Search query logs (used for recent/popular suggestions) are append-only and are not currently cleared automatically; there is no UI/API to clear them.
- Resetting a password revokes all of that user's sessions and refresh-token families immediately.
- Comparison, contract risk, and action-item results are never persisted — recomputed fresh on every request.

---

## 6. Non-Functional Requirements

### 6.1 Security

- **NFR-SEC-1:** The system shall not index files identified as sensitive (credentials/keys) unless the user explicitly opts in for that scan. (See FR-SENS-3–8.)
- **NFR-SEC-2:** CORS origins accepted by the backend shall be explicitly configured (`BACKEND_CORS_ORIGINS`), not left open by default.
- **NFR-SEC-3:** Secrets (JWT signing keys, database credentials, `GROQ_API_KEY`, SMTP credentials) shall be supplied via environment configuration/key files, never hardcoded, and any default placeholder value shall be changed before any non-local deployment.
- **NFR-SEC-4:** Every folder/file/search/admin endpoint shall require a valid access token and the specific permission code it declares; there is no unauthenticated access to any of these resources.
- **NFR-SEC-5:** The AI answer, tagging, entity extraction, summary, comparison, contract-risk, and action-item features shall each send only the text relevant to their own request (retrieved chunks, or the file(s)' own text) to the configured LLM provider — no other indexed content, file paths, credentials, or system metadata.
- **NFR-SEC-6:** The LLM provider API key (`GROQ_API_KEY`) shall be supplied via environment configuration only and never logged or echoed back in API responses.
- **NFR-SEC-7:** The query-rewriting and search-suggestion steps shall send only the user's own query text (and, for suggestions, the fixed list of known document categories) to the LLM provider — no indexed file content, file paths, or system metadata.
- **NFR-SEC-8:** Passwords shall be hashed with Argon2id; refresh tokens, email-verification tokens, and password-reset tokens shall be stored only as salted hashes, never in plaintext. Access/refresh tokens shall be signed with RS256 using a keypair not checked into version control.
- **NFR-SEC-9:** A user flagged `is_superadmin` (or a legacy token with no organization claim) shall bypass organization-scoping filters on folder/file/search queries; this is the one documented, intentional exception to per-organization data isolation and shall remain restricted to the platform's bootstrap Super Admin account(s).
- **NFR-SEC-10:** The system shall apply per-route rate limiting to registration (3/min), login (5/min), and forgot-password (3/min) to slow down credential-stuffing and enumeration attempts.
- **NFR-SEC-11:** The system shall respond identically to resend-verification and forgot-password requests regardless of whether the target email exists, to avoid confirming account existence to an attacker.
- **NFR-SEC-12:** HTTP responses shall include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a restrictive `Content-Security-Policy`, and HSTS in production.

### 6.2 Performance

- **NFR-PERF-1:** A folder scan estimate shall run as a read-only, checksum-free walk so it stays cheap enough to run synchronously ahead of a real scan.
- **NFR-PERF-2:** Estimated scan duration shall be surfaced to the user before committing to a full scan, based on configurable throughput assumptions (`ESTIMATE_FILES_PER_SECOND`, `ESTIMATE_BYTES_PER_SECOND`).
- **NFR-PERF-3:** Files at or above `LARGE_FILE_THRESHOLD_BYTES` (default 50 MB) shall be flagged to the user as likely to slow down processing.
- **NFR-PERF-4:** A background scan shall not block the API process from serving other requests; it shall run on a separate thread and report progress asynchronously.
- **NFR-PERF-5:** Search-suggestion requests shall be debounced client-side and shall not block or delay the primary search/chat request.
- **NFR-PERF-6:** Access tokens shall be short-lived (15 minutes) so that a compromised token has a bounded window of usefulness, while refresh happens transparently to the user.

### 6.3 Reliability / Data Integrity

- **NFR-REL-1:** Scans shall be idempotent with respect to unchanged files: an unchanged file (same mtime) is left untouched; same checksum with a changed mtime updates only the timestamp, without reprocessing.
- **NFR-REL-2:** Any folder-path access failure shall be surfaced with a specific, actionable error rather than a generic failure.
- **NFR-REL-3:** A failure in any best-effort enrichment step (tagging, entity extraction) shall never change a successfully-indexed file's status to failed.
- **NFR-REL-4:** A failure to send a transactional email (verification, reset, invitation, login alert) shall never fail the underlying auth/organization action that triggered it.

### 6.4 Usability

- **NFR-USE-1:** Before adding a folder or running a scan that would touch sensitive files, the user shall see a clear warning and an explicit choice, with the safe option (skip) as the default.
- **NFR-USE-2:** Scan/estimate results shall be presented with human-readable counts, durations, and byte sizes, not raw numbers alone.
- **NFR-USE-3:** The active chat scope (folder or file) shall be visually unambiguous at all times, with an explicit way to exit it.
- **NFR-USE-4:** A user shall never be left without actionable feedback after a failed login, registration, or password action — each failure mode (locked, unverified, wrong password, expired token) shall have a distinct, specific message.

### 6.5 Maintainability

- **NFR-MAINT-1:** Backend code shall follow the layered `endpoint -> service -> repository -> model` architecture with schemas decoupled from ORM models.
- **NFR-MAINT-2:** Database schema changes shall be made exclusively through Alembic migrations.

### 6.6 Portability

- **NFR-PORT-1:** The backend and frontend shall each run standalone (local dev) or together via Docker Compose, on Windows, Linux, or macOS hosts.

---

## 7. System Architecture Summary

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full, current architecture (service map, data model, indexing pipeline, search/chat scoping, real-time scan progress, frontend structure, and known caveats), and [`DFD.md`](DFD.md) for data-flow diagrams covering authentication, indexing, search/chat, and file analysis.

---

## 8. Future Work / Open Items

- Enforce the `subscription_plan`/storage-quota fields that already exist on `organizations` (currently informational only).
- Provide a UI for organization admins to see and clear old search-query-log entries.
- Consider a superadmin-facing cross-organization console, rather than the current implicit bypass, so cross-org access is auditable through the UI rather than only via the API contract (see NFR-SEC-9).
- Expand the sensitive-file detection list (e.g. cloud provider credential file conventions, additional key formats) and consider making the pattern list configurable per organization.
- Consider surfacing indexing failures (`status = failed`, `error_message`) more prominently in the UI.
- Evaluate direct file upload as an alternative ingestion path alongside folder monitoring.
- Reconcile the two AI-answer confidence models (model-self-reported for non-streaming vs. retrieval-similarity-derived for streaming) into a single consistent measure, or clearly document the difference to end users.
- Support additional/alternate LLM providers behind the current Groq-specific `GroqClient`.
- Evaluate whether query rewriting measurably improves retrieval quality in practice and consider caching rewrites for repeated/similar queries.
- Consider condensing older conversation turns (summarization) instead of a hard cutoff at 12/20 messages.
- Backfill `folder_id` chunk metadata for files embedded before folder-scoped chat existed (currently requires a rescan to become folder-filterable).
- Persist comparison/contract-risk/action-item results optionally, for documents where re-running the same analysis repeatedly would be wasteful.
- Add an `is_current` flag to session listings once the access token carries a `family_id` claim, so a user can tell which session is their present one.
- Automatically generate a file summary at index time (currently on-demand only) as an option, trading upfront cost for instant availability.

---

## 9. Approval / Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-14 | Initial SRS covering folder management, scanning/indexing, sensitive-file detection, search, and file browsing as currently implemented. |
| 1.1 | 2026-07-14 | Added AI-generated search answers (Groq): non-streaming JSON-mode answers and streamed (SSE) answers with live token rendering, cancel, retry, and copy in the UI. |
| 1.2 | 2026-07-14 | Replaced the single-query search page with a full multi-turn chat interface (Markdown rendering, code blocks, clickable citations, suggested questions, auto-scroll, dark mode); added conversation history support end-to-end; added Groq-backed query rewriting before retrieval. |
| 2.0 | 2026-07-20 | Added automatic document classification (tags with colored/icon badges and filtering); structured entity extraction; on-demand document summaries; search-box autocomplete (recent/popular/AI-generated suggestions); folder-scoped and file-scoped chat with isolated conversation memory; background scanning with live WebSocket progress; file content viewing. Split detailed architecture and API documentation out into `ARCHITECTURE.md` and `API_REFERENCE.md`. |
| 3.0 | 2026-07-30 | Added full authentication and account security (self-registration, email verification, login with lockout, RS256 access/refresh tokens with rotation and reuse detection, password reset/change, session management, security notification emails). Added multi-tenant organizations (every self-registered user provisioned with their own private organization; the platform's first-ever user becomes Super Admin of a platform-owner organization), invitations, member management, and 5-role/13-permission RBAC enforced on every folder/file/search/admin endpoint. Added organization-scoped data isolation across folders, files, and search/chat retrieval. Added on-demand file comparison, contract risk analysis, and action-item extraction. Added companion `DFD.md` data-flow diagrams. Moved authentication out of "out of scope" and into the core specification. |
