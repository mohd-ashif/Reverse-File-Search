# API Reference

Base URL: `http://localhost:8000` · Base prefix: **`/api/v1`** · All bodies are JSON unless noted. Interactive docs (Swagger UI) are always available at `/docs`, ReDoc at `/redoc`.

---

## Health

### `GET /health`
Liveness/readiness check.

**Response `200`**
```json
{ "status": "ok" }
```

---

## Folders

### `GET /folders/`
List all monitored folders.

**Response `200`** → `FolderRead[]`
```json
[{ "id": 1, "path": "C:/Docs", "is_active": true, "created_at": "...", "updated_at": "..." }]
```

### `POST /folders/`
Register a folder to monitor.

**Body**
```json
{ "path": "C:/Docs" }
```
**Response `201`** → `FolderRead`

**Errors:** `400` invalid/too-broad path (e.g. a drive root) · `403` permission denied · `404` path doesn't exist · `409` already monitored · `423` locked by another process · `503` network path unreachable.

### `POST /folders/estimate`
Dry-run scan preview — validates the path and walks it read-only; nothing is persisted.

**Body:** same as above (`{ "path": "..." }`)

**Response `200`** → `FolderEstimate`
```json
{
  "path": "C:/Docs",
  "estimated_files": 120,
  "estimated_supported_files": 98,
  "unsupported_files": 22,
  "approx_scan_seconds": 4.3,
  "estimated_storage_bytes": 52428800,
  "large_files_detected": 1,
  "large_file_threshold_bytes": 50000000,
  "sensitive_files_detected": 2,
  "sensitive_file_samples": [".env", "id_rsa"]
}
```
Same path-validation errors as `POST /folders/`.

### `DELETE /folders/{folder_id}`
Stop monitoring a folder — cascades to delete its indexed files, chunks, and vector-store embeddings.

**Response:** `204` · **Errors:** `404` not found.

### `POST /folders/{folder_id}/scan?skip_sensitive=true`
Synchronous scan + index — blocks until the whole folder is reconciled and all pending files are processed.

**Query:** `skip_sensitive` (bool, default `true`)

**Response `200`**
```json
{
  "scan": { "folder_id": 1, "added": 3, "modified": 1, "deleted": 0, "skipped": 40, "skipped_sensitive": 2 },
  "index": { "extracted": 4, "embedded": 4, "failed": 0 }
}
```
**Errors:** `404` folder not found.

### `POST /folders/{folder_id}/scan/start?skip_sensitive=true`
Kicks off the same scan + index in a background thread and returns immediately. Connect to `WS /ws/scan/{scan_id}` right after to watch live progress.

**Response `200`**
```json
{ "scan_id": "3f9c2b1a..." }
```
**Errors:** `404` folder not found.

---

## Files

### `GET /files/?folder_id=&tag=`
List indexed files, optionally filtered by folder and/or category tag (case-insensitive exact match).

**Response `200`** → `IndexedFileRead[]`

### `GET /files/tags?folder_id=`
Tags for every file that has at least one, optionally scoped to a folder. Bulk lookup (avoids one request per file).

**Response `200`** → `FileTagsRead[]`
```json
[{ "file_id": 12, "tags": ["Invoice", "Tax"] }]
```

### `GET /files/{file_id}`
Single indexed file record. **Errors:** `404`.

### `GET /files/{file_id}/content`
Streams the original file bytes (`inline` content-disposition, MIME type guessed from filename) — used by the "View File" link in the UI. **Errors:** `404` (record or file missing from disk).

### `GET /files/{file_id}/tags`
Tags for one file. **Response** → `FileTagsRead` (`{file_id, tags: []}` if none). **Errors:** `404` file not found.

### `GET /files/{file_id}/entities`
Structured fields extracted from the file (invoice number, vendor, GST, PAN, amount, date, email, phone, address, bank, PO number, contract number — each `string | null`). **Errors:** `404` if no entities have been extracted yet (Groq not configured, extraction failed, or file has no such content).

### `GET /files/{file_id}/summary`
Previously generated summary, if any. **Errors:** `404` none generated yet.

### `POST /files/{file_id}/summary`
Generate (or regenerate) a structured summary for the file, on demand.

**Response `201`** → `FileSummaryRead`
```json
{
  "id": 5, "file_id": 12,
  "executive_summary": "...",
  "key_points": ["..."], "important_dates": ["Sept 30, 2024 — GST filing deadline"],
  "people": ["..."], "organizations": ["..."], "risks": ["..."], "action_items": ["..."],
  "model": "llama-3.3-70b-versatile",
  "created_at": "...", "updated_at": "..."
}
```
**Errors:** `404` file not found · `503` no LLM provider configured · `422` couldn't extract text (empty/unreadable file) · `502` provider call failed.

---

## Search & Chat

### `POST /search/`
Non-streaming reverse file search, with an optional synthesized AI answer.

**Body**
```json
{
  "query": "unpaid invoices",
  "top_k": 10,
  "generate_answer": false,
  "history": [{ "role": "user", "content": "..." }],
  "rewrite_query": true,
  "folder_id": null,
  "file_id": null
}
```
| Field | Default | Notes |
|---|---|---|
| `query` | — | required |
| `top_k` | `10` | max results (ignored when `file_id` is set — returns the whole file) |
| `generate_answer` | `false` | if `true`, also returns a non-streamed AI answer |
| `history` | `[]` | prior turns, capped server-side to the last 12 |
| `rewrite_query` | `true` | disable to force embedding the literal query text |
| `folder_id` | `null` | restrict retrieval to files inside this folder |
| `file_id` | `null` | restrict retrieval to one file's own full content (takes precedence over `folder_id`) |

**Response `200`**
```json
{
  "results": [{ "file_id": 12, "filename": "invoice.pdf", "chunk_text": "...", "score": 0.83 }],
  "answer": { "text": "...", "sources": ["invoice.pdf"], "confidence": 0.91 },
  "rewritten_query": "unpaid invoices outstanding balance"
}
```
`answer` is `null` if `generate_answer` was `false`, no provider is configured, or the provider call failed.

### `POST /search/stream`
Same retrieval/scoping rules as above; always generates an answer, streamed as `text/event-stream`. Body: same shape minus `generate_answer` (irrelevant — always on).

**Event sequence** (each frame is `data: <json>\n\n`):

| `type` | Payload | When |
|---|---|---|
| `query` | `{original_query, rewritten_query}` | First, before retrieval results |
| `results` | `{results: SearchResultItem[]}` | Once retrieval completes |
| `meta` | `{sources: string[], confidence: number}` | Before the first token; confidence derived from retrieval similarity, not the model |
| `token` | `{text: string}` | Zero or more, in order |
| `done` | `{}` | Terminates a successful stream |
| `error` | `{message: string}` | Terminates the stream on failure |

Cancelling the client request (aborting the fetch) closes the underlying Groq connection server-side.

### `GET /search/suggestions?q=`
Autocomplete data for the search box. `q` is the partial text typed so far (may be empty).

**Response `200`**
```json
{
  "recent": ["unpaid invoices"],
  "popular": ["GST invoices this year"],
  "ai_generated": ["Show GST invoices", "Invoices over ₹50,000"]
}
```
All three lists are best-effort — `ai_generated` is `[]` if no LLM provider is configured or the call fails; `recent`/`popular` are `[]` if nothing has been searched yet.

---

## WebSocket

### `WS /ws/scan/{scan_id}`
Live progress feed for a scan started via `POST /folders/{id}/scan/start`. The client sends nothing meaningful; the server pushes JSON frames:

**Progress**
```json
{
  "type": "progress", "scan_id": "...", "stage": "generating_embeddings",
  "current_file": "invoice.pdf", "files_processed": 3, "files_total": 10,
  "files_remaining": 7, "estimated_remaining_seconds": 12.4, "elapsed_seconds": 5.1
}
```
`stage` is one of: `finding_files`, `reading_metadata`, `extracting_text`, `generating_embeddings`, `saving_to_database`, `finalizing`.

**Summary** (terminal, success)
```json
{
  "type": "summary", "scan_id": "...",
  "scan": { "folder_id": 1, "added": 3, "modified": 1, "deleted": 0, "skipped": 40, "skipped_sensitive": 2 },
  "index": { "extracted": 4, "embedded": 4, "failed": 0 },
  "succeeded_files": ["a.pdf"], "failed_files": [{ "filename": "b.pdf", "path": "...", "error": "..." }],
  "elapsed_seconds": 8.9
}
```

**Error** (terminal, failure)
```json
{ "type": "error", "scan_id": "...", "message": "...", "elapsed_seconds": 2.0 }
```

---

## Error format

All non-2xx responses use FastAPI's standard shape:
```json
{ "detail": "human-readable message" }
```
or, for validation errors (`422`), FastAPI's field-error array under `detail`. The frontend's `ApiError` class normalizes both into a message plus a `fieldErrors` array.
