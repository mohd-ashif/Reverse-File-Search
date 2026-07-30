# Data Flow Diagrams (DFD)

## Reverse File Search

**Version:** 1.0
**Date:** 2026-07-30
**Companion to:** [`SRS.md`](SRS.md) (requirements), [`ARCHITECTURE.md`](ARCHITECTURE.md) (service map), [`USER_GUIDE.md`](USER_GUIDE.md) (user-facing walkthrough)

This document describes how data moves through Reverse File Search, from external entities (the browser user, third-party services) through the backend's processes into its data stores and back out again. Diagrams use the Yourdon/DeMarco convention (external entity = box, process = rounded box, data store = open-ended bar, flow = labeled arrow), rendered as Mermaid flowcharts.

---

## 0. External Entities & Data Stores (used throughout)

| External Entity | Role |
|---|---|
| **User (Browser)** | An authenticated (or, for a handful of flows, anonymous/pre-auth) person interacting with the React SPA |
| **Groq Cloud** | Third-party LLM API — query rewriting, AI answers, tagging, entity extraction, summaries, suggestions, file comparison, contract risk analysis, action-item extraction |
| **SMTP Server** | Third-party mail relay (Gmail SMTP in current config) — verification, password-reset, invitation, and security-notification emails |
| **Local Filesystem** | The disk the backend process can read — monitored folders and the files inside them |

| Data Store | Contents |
|---|---|
| **D1 — Relational DB (PostgreSQL)** | All structured metadata: users, organizations, roles/permissions, sessions/tokens, folders, files, chunks metadata, tags, entities, summaries, search logs, audit/login history (19 tables total — see §5 of the SRS) |
| **D2 — Vector Store (Chroma)** | Chunk embeddings, keyed by `chroma_id`, filterable by `organization_id` / `folder_id` / `file_id` metadata |
| **D3 — JWT Keypair (disk)** | RS256 private/public key files used to sign and verify access/refresh tokens |

---

## 1. Context Diagram (Level 0)

The whole system as a single process, showing every external entity it exchanges data with.

```mermaid
flowchart LR
    User(["User (Browser)"])
    Groq[["Groq Cloud (LLM)"]]
    SMTP[["SMTP Server"]]
    FS[["Local Filesystem"]]

    System(("0\nReverse File Search"))

    User -- "credentials, folder paths,\nqueries, chat messages,\nfile actions" --> System
    System -- "auth tokens, scan progress,\nsearch results, AI answers,\nfile listings/analysis" --> User

    System -- "rewrite/answer/classify/\nextract/summarize/compare\nrequests (text only)" --> Groq
    Groq -- "generated text (JSON/tokens)" --> System

    System -- "verification/reset/invite/\nalert emails" --> SMTP
    SMTP -- "delivery status" --> System

    System -- "directory walks,\nfile reads" --> FS
    FS -- "file bytes, metadata\n(size, mtime)" --> System
```

---

## 2. Level 1 — Major Subsystems

Six cooperating process groups inside the backend, and how data flows between them and the two internal data stores.

```mermaid
flowchart TB
    User(["User (Browser)"])
    Groq[["Groq Cloud"]]
    SMTP[["SMTP Server"]]
    FS[["Local Filesystem"]]

    P1("1.0\nAuthentication &\nAccount Security")
    P2("2.0\nOrganizations,\nRoles & Invitations")
    P3("3.0\nFolder Monitoring &\nIndexing Pipeline")
    P4("4.0\nSearch, Chat &\nAI Answers")
    P5("5.0\nOn-Demand File\nAnalysis")
    P6("6.0\nAudit, Sessions &\nSecurity Logging")

    D1[("D1 Relational DB")]
    D2[("D2 Vector Store")]
    D3[("D3 JWT Keypair")]

    User -- "register/login/refresh/\npassword flows" --> P1
    P1 -- "access+refresh tokens,\nverification/reset emails" --> User
    P1 <-- "sign/verify tokens" --> D3
    P1 <-- "user rows, tokens,\nlockout state" --> D1
    P1 -- "verification, reset,\nlogin-alert emails" --> SMTP
    P1 -- "login/logout/reset events" --> P6

    User -- "org settings, invite,\nmember/role actions" --> P2
    P2 -- "org profile, member list,\ninvitation status" --> User
    P2 <-- "orgs, roles, permissions,\nmemberships, invitations" --> D1
    P2 -- "invitation emails" --> SMTP
    P2 -- "org/role/invite events" --> P6

    User -- "add/scan/remove folder" --> P3
    P3 -- "scan progress (WS),\nfile listings, tags" --> User
    P3 <-- "walk directories,\nread file bytes" --> FS
    P3 <-- "folders, files, chunks,\ntags, entities meta" --> D1
    P3 -- "chunk embeddings" --> D2
    P3 -- "classify/extract text" --> Groq

    User -- "search query,\nchat message" --> P4
    P4 -- "ranked results,\nstreamed answer" --> User
    P4 <-- "similarity search\n(org/folder/file filtered)" --> D2
    P4 <-- "file metadata,\nquery logs" --> D1
    P4 -- "rewrite/answer/suggest" --> Groq

    User -- "compare/risk/action-item\nrequest" --> P5
    P5 -- "comparison/risk/\naction-item result" --> User
    P5 <-- "read file text" --> D1
    P5 -- "analyze text" --> Groq

    P1 & P2 & P3 & P4 & P5 -- "action records" --> P6
    P6 <-- "audit_logs,\nlogin_history,\nuser_sessions" --> D1
```

---

## 3. Level 2 — Registration & Authentication (Process 1.0)

Detail of what happens inside "Authentication & Account Security" for the two highest-traffic flows: self-registration and login.

```mermaid
flowchart TB
    User(["User (Browser)"])
    SMTP[["SMTP Server"]]
    D1[("D1 Relational DB")]
    D3[("D3 JWT Keypair")]

    P1a("1.1\nValidate & create\nuser account")
    P1b("1.2\nProvision organization\n(new org, or platform\norg for the first-ever user)")
    P1c("1.3\nAssign role &\norg membership")
    P1d("1.4\nIssue email-verification\ntoken")
    P1e("1.5\nValidate credentials,\ncheck lockout/verification")
    P1f("1.6\nIssue access + refresh\ntoken pair")
    P1g("1.7\nRotate / revoke\nrefresh tokens")

    User -- "email, password,\nfull name" --> P1a
    P1a -- "reject: email\nalready exists" --> User
    P1a <-- "check duplicate,\ninsert user row" --> D1
    P1a --> P1b
    P1b <-- "create/find organization\n(is_platform_owner_org flag)" --> D1
    P1b --> P1c
    P1c <-- "insert role assignment +\norg membership row" --> D1
    P1c --> P1d
    P1d <-- "store hashed token\n(24h expiry)" --> D1
    P1d -- "verification link" --> SMTP
    SMTP -- "email" --> User

    User -- "email, password" --> P1e
    P1e <-- "read user, failed_login_count,\nlocked_until, is_verified" --> D1
    P1e -- "423 locked / 401 invalid /\n401 unverified" --> User
    P1e -- "increment failure count\nor reset on success" --> D1
    P1e --> P1f
    P1f <-- "sign RS256 tokens" --> D3
    P1f -- "store hashed refresh token\n+ family id, create session" --> D1
    P1f -- "access token (body),\nrefresh token (httpOnly\ncookie + body)" --> User

    User -- "POST /auth/refresh" --> P1g
    P1g <-- "verify family not revoked;\nreuse ⇒ revoke whole family" --> D1
    P1g -- "new token pair,\nor 401 on reuse" --> User
```

**Key business rules embedded in this flow:**
- The very first user ever registered on the system becomes **Super Admin** and owns a brand-new **platform-owner organization**.
- Every subsequent self-registered user gets **their own new, separate organization** (Organization Admin/Owner of it) — folders and files never cross this boundary.
- 5 consecutive bad passwords → account locked 15 minutes (423).
- A reused (already-rotated) refresh token revokes its entire token family and session — a session-hijack containment measure.

---

## 4. Level 2 — Folder Scan & Indexing Pipeline (Process 3.0)

```mermaid
flowchart TB
    User(["User (Browser)"])
    FS[["Local Filesystem"]]
    Groq[["Groq Cloud"]]
    D1[("D1 Relational DB")]
    D2[("D2 Vector Store")]

    P3a("3.1\nValidate path &\nestimate scan")
    P3b("3.2\nWalk directory,\ndetect sensitive files")
    P3c("3.3\nReconcile files\n(added/modified/deleted)")
    P3d("3.4\nExtract text\n(PDF/DOCX/TXT/MD/XLSX/OCR)")
    P3e("3.5\nChunk & embed")
    P3f("3.6\nClassify tags &\nextract entities (best-effort)")
    P3g("3.7\nEmit progress\n(WebSocket)")

    User -- "folder path" --> P3a
    P3a <-- "reject: missing/permission/\nlocked/network/too-broad" --> FS
    P3a -- "estimate: counts, size,\nduration, sensitive files" --> User

    User -- "Scan / Scan (background)" --> P3b
    P3b <-- "recursive walk,\nskip ignored dirs" --> FS
    P3b -- "sensitive file list" --> User
    P3b --> P3c
    P3c <-- "compare mtime/checksum\nvs indexed_files rows" --> D1
    P3c --> P3d
    P3d <-- "read file bytes" --> FS
    P3d --> P3e
    P3e -- "store chunk metadata" --> D1
    P3e -- "store embeddings\n(org/folder/file-tagged)" --> D2
    P3e --> P3f
    P3f -- "file text" --> Groq
    Groq -- "tags, structured fields" --> P3f
    P3f -- "store tags/entities\n(never fails the index)" --> D1
    P3c & P3d & P3e & P3f --> P3g
    P3g -- "stage, file, counts,\nETA, terminal summary" --> User
```

**Key business rules embedded in this flow:**
- Only files with a supported extension are extracted/embedded; everything else is counted but skipped.
- Sensitive-looking files (`.env`, `.pem`, `id_rsa`, etc.) are excluded from extraction/embedding by default; the user can override per-scan.
- A checksum match on a changed-mtime file updates only the timestamp — no re-extraction.
- Tag/entity generation failures never flip a successfully-indexed file to `failed`.
- All rows and embeddings created here are stamped with the acting user's `organization_id`.

---

## 5. Level 2 — Search & Chat Retrieval (Process 4.0)

```mermaid
flowchart TB
    User(["User (Browser)"])
    Groq[["Groq Cloud"]]
    D1[("D1 Relational DB")]
    D2[("D2 Vector Store")]

    P4a("4.1\nRewrite query\n(best-effort)")
    P4b("4.2\nEmbed query &\nsimilarity search")
    P4c("4.3\nApply scope filter\n(org, + optional folder/file)")
    P4d("4.4\nSynthesize grounded\nanswer (streamed)")
    P4e("4.5\nLog query &\nderive suggestions")

    User -- "query + history +\nscope (none/folder/file)" --> P4a
    P4a -- "rewrite via LLM,\nfall back to original\non failure/disabled" --> Groq
    P4a --> P4b
    P4b -- "query embedding" --> D2
    P4b --> P4c
    P4c -- "filter: organization_id\n+ folder_id or file_id" --> D2
    D2 -- "ranked chunks +\nsimilarity scores" --> P4c
    P4c -- "join filename/metadata" --> D1
    P4c -- "results event (SSE)\nor JSON results" --> User
    P4c --> P4d
    P4d -- "retrieved chunks +\noriginal query + history" --> Groq
    Groq -- "streamed tokens /\nJSON answer + confidence" --> P4d
    P4d -- "token events / answer,\nsources, confidence" --> User
    P4c --> P4e
    P4e -- "insert search_query_logs row" --> D1
    P4e -- "AI-generated suggestions" --> Groq
    P4e -- "recent/popular/AI\nsuggestions" --> User
```

**Key business rules embedded in this flow:**
- File-scoped retrieval bypasses similarity search entirely — it returns that file's full chunk set in document order.
- Retrieval is always filtered by the caller's `organization_id` (the one documented exception: a superadmin/legacy token with no `org` claim applies no tenant filter).
- The AI is shown only the retrieved chunk text; if that's insufficient, the fixed string `"I couldn't find enough information."` is returned instead of a guess.
- Conversation `history` is never embedded for retrieval — only the current turn's (rewritten) query is.

---

## 6. Level 2 — On-Demand File Analysis (Process 5.0)

Covers document summaries, file comparison, contract risk analysis, and action-item extraction — all stateless-per-request except summaries, which are cached.

```mermaid
flowchart TB
    User(["User (Browser)"])
    Groq[["Groq Cloud"]]
    D1[("D1 Relational DB")]

    P5a("5.1\nSummary\n(cached after first generation)")
    P5b("5.2\nFile Comparison\n(two files)")
    P5c("5.3\nContract Risk Analysis\n(5 fixed categories)")
    P5d("5.4\nAction Item Extraction")

    User -- "Generate summary" --> P5a
    P5a <-- "re-extract file text" --> D1
    P5a -- "text" --> Groq
    Groq -- "executive summary, key points,\ndates, people, orgs, risks" --> P5a
    P5a -- "persist file_summaries row" --> D1
    P5a -- "summary (or cached copy)" --> User

    User -- "Compare file A + B" --> P5b
    P5b <-- "extract both files' text\n(capped 12k chars each)" --> D1
    P5b -- "both texts" --> Groq
    Groq -- "summary, differences,\nadded/removed clauses,\nfinancial changes" --> P5b
    P5b -- "comparison result\n(not persisted)" --> User

    User -- "Analyze contract risk" --> P5c
    P5c <-- "extract text (capped 24k)" --> D1
    P5c -- "text" --> Groq
    Groq -- "5-category risk flags\n(present + explanation)" --> P5c
    P5c -- "risk result (not persisted)" --> User

    User -- "Extract action items" --> P5d
    P5d <-- "extract text" --> D1
    P5d -- "text" --> Groq
    Groq -- "person, task, deadline,\npriority per item" --> P5d
    P5d -- "action items\n(not persisted)" --> User
```

**Key business rules embedded in this flow:**
- All four analyses require `FILE_READ` permission and are org-scoped (the file must belong to the caller's organization).
- Comparison/risk/action-items are recomputed on every request (no caching); only the on-demand summary is persisted (`file_summaries`) and reused until explicitly regenerated.
- A misconfigured or unreachable LLM provider yields a specific `503` for all four — never a silent guess.
- Contract risk analysis always returns exactly 5 categories (Missing Signature, Unlimited Liability, Auto-Renewal, Late Fees, Termination Clause); any category the model omits is backfilled as `present=false`.

---

## 7. Data Isolation Summary (cross-cutting)

Every process above that touches `D1`/`D2` for folder/file/search data applies the same tenant boundary:

```mermaid
flowchart LR
    Token["Caller's access token\n(carries org claim)"] -->|"org present"| Filtered["Query/embedding filter:\norganization_id = token.org"]
    Token -->|"org absent\n(superadmin / legacy token only)"| Unfiltered["No tenant filter applied\n(cross-org visibility)"]
    Filtered --> Result["Rows/chunks returned"]
    Unfiltered --> Result
```

This is the one intentional gap in per-organization isolation, and it is documented as such in [`SRS.md` §6.1](SRS.md#61-security).

