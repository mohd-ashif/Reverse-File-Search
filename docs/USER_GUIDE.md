# User Guide

A complete walkthrough of everything Reverse File Search can do today. For setup, see [`INSTALLATION.md`](INSTALLATION.md). For the full requirements list, see [`SRS.md`](SRS.md). For internals, see [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`API_REFERENCE.md`](API_REFERENCE.md).

The app has four pages, reachable from the top nav: **Overview**, **Folders**, **Files**, **Chat**.

---

## 1. Overview

A dashboard snapshot: how many folders are monitored, how many files are indexed, how many failed, and a breakdown by indexing status (pending / extracted / indexed / failed). First-time users see a **Getting Started** panel with next-step guidance until at least one folder is added. Quick links jump to Folders, Files, or Chat.

---

## 2. Folders — register, preview, scan

### Adding a folder

Click **Add folder** and enter an absolute path. Before it's registered, you'll see a **preview**: estimated file count, how many are of a supported type, an approximate scan duration, estimated storage size, how many files are "large" (≥50MB by default), and — importantly — how many look like **sensitive files** (see below). Nothing is indexed at this step; adding a folder only registers the path.

Paths are rejected up front with a specific reason if they're: missing, not a directory, permission-denied, locked by another process, an unreachable network location, or "too broad" (e.g. a drive root) — rather than a generic error.

### Sensitive file protection

The app automatically flags files that look like credentials or secrets: `.env`/`.env.*`, `.pem`, `.key`, `.pfx`, `.kdbx`, `wallet.dat`, `id_rsa`/`id_ed25519` (and `.pub` variants), `credentials.json`, `passwords.txt`.

When you click **Scan** on a folder and sensitive files are found, a dialog offers three choices:

| Choice | Effect |
|---|---|
| **Skip sensitive files** (default) | Scan proceeds; these files are never opened, chunked, or embedded. A previously-indexed file that newly matches this pattern is also removed. |
| **Continue anyway** | Scan proceeds and indexes them like any other supported file. |
| **Cancel** | Nothing happens. |

If no sensitive files are found, scanning proceeds immediately with no dialog. **Recommendation:** leave the default unless you specifically intend to make a credential file searchable.

### Scanning

Clicking **Scan** kicks off a background scan and opens a **live progress dialog** showing each stage in order — finding files → reading metadata → extracting text → generating embeddings → saving to database → finalizing — with a progress bar, current filename, processed/remaining counts, elapsed time, and an ETA. You can close the dialog ("Run in background") and it keeps running; reopening later isn't currently supported mid-run, but the folder/file lists refresh automatically once it finishes. On completion you see a success summary (added/modified/deleted/skipped counts, how many were indexed) and a list of any files that failed, with the reason for each.

A scan only re-processes what actually changed: unchanged files (same modification time) are skipped entirely; a file with a changed modification time but the same content checksum just has its timestamp updated (no re-extraction); files deleted from disk are removed from the index; only genuinely new or changed content is re-extracted and re-embedded.

### Removing a folder

**Remove** stops monitoring it and deletes all of its indexed files, chunks, and vector-store embeddings. This cannot be undone (the files on disk are untouched — only the index is removed).

### Chat with a folder

Each folder row has a **Chat** button — see §4.2 below.

---

## 3. Files — browse, filter, inspect

The **Files** page lists every indexed file: filename, type, size, status (pending/extracted/indexed/failed), assigned tags, and when it was indexed. You can:
- **Search** by filename (debounced live filter).
- **Filter** by folder and/or by category **tag**.
- **Sort** by filename, size, status, or indexed date.
- Page through results.

### Automatic classification tags

After a file finishes indexing, it's automatically classified into one or more short category tags — Invoice, Contract, Resume, Tax, Purchase Order, Medical Record, Salary Slip, Bank Statement, Receipt, Letter, or a sensible custom category if none of those fit. Each tag renders as a small colored badge with an icon (e.g. a receipt icon for Receipt, a shopping-cart icon for Purchase Order), shown both in the files table and in a file's detail view. Use the **tag filter** dropdown on the Files page to see only files of a given category. This step is best-effort: if no AI provider is configured, files simply have no tags, and everything else keeps working.

### File detail view

Clicking a row (or a citation badge in Chat) opens a detail dialog showing: status, type, size, path, checksum, folder, timestamps, tags, and any error message. From here you can:
- **View File** — opens the original file in a new browser tab.
- **Chat** — switches the dialog into a mini conversation scoped to just this file (see §4.3).
- View or **generate a summary** — see below.

### On-demand summaries

Each file's detail view offers a **structured summary**: an executive summary paragraph, key points, important dates (each described, e.g. "Sept 30, 2024 — GST filing deadline"), people mentioned, organizations mentioned, risks, and action items — all grounded strictly in the file's own text (never invented). Summaries aren't generated automatically at index time; you request one explicitly, and it's cached until you request it again.

### Extracted business fields

For invoice-like documents, the system also extracts structured fields in the background during indexing — invoice number, vendor, customer, GST/PAN numbers, amount, date, email, phone, address, bank, PO number, contract number — available via the API (`GET /files/{id}/entities`) for any integration that wants structured data rather than free text.

---

## 4. Chat — talk to your files

The **Chat** page (nav label "Chat", route `/search`) is a full multi-turn conversation with an AI grounded only in your indexed files.

### 4.1 Starting a conversation

With an empty conversation, you'll see a few clickable **suggested questions**. Otherwise, type and press **Enter** (Shift+Enter for a newline) or tap send.

As you type in the search box, an **autocomplete dropdown** appears with up to three sections — **Recent searches** (your own past queries), **Popular searches** (the most frequent queries across all usage), and **AI-generated searches** (smart suggestions, e.g. "Show GST invoices", "Invoices over ₹50,000", "Contracts signed last month") — updating live as you keep typing.

### 4.2 Folder-scoped chat

From the **Folders** page, click **Chat** on any folder row. You land on the Chat page with a banner reading "Chatting within folder: `<path>`" and folder-flavored starter prompts ("What invoices are unpaid?", "What's the largest purchase?", "Who spent the most?"). Every answer in this conversation is grounded **only** in documents inside that folder — nothing else in your index is considered. Click **Exit folder chat** in the banner to return to the unscoped, all-files conversation. Switching between folders (or back to global) always starts a fresh conversation — history doesn't leak across scopes.

### 4.3 File-scoped chat

Open any file's detail view and click **Chat**. This swaps the dialog into its own mini conversation, with prompts like "Summarize this file.", "Explain clause 4.", "Who signed?", "When was payment made?" — answered using **only that file's content**, in full (not a similarity-searched excerpt), so specific questions about a particular clause or detail aren't at the mercy of a search match missing it. Click **Details** to switch back to the file's metadata view; re-opening the dialog for a different file starts a new conversation.

### 4.4 What you see in a response, in order

1. **Thinking…** — a typing indicator before the first word arrives.
2. The answer **typing itself out** live, rendered as full Markdown (headings, lists, tables) with syntax-aware, copyable code blocks.
3. A **"Searched for: …"** note if your query was rephrased for better retrieval (see §4.6) — omitted for file-scoped chat, since nothing is rewritten there.
4. **Sources** — clickable badges naming the file(s) the answer is based on; clicking one that matches an indexed file opens its detail view. These come directly from what was actually retrieved — never invented.
5. **Confidence** — a percentage indicating how well your indexed content supports the answer.

### 4.5 Per-message controls

| Control | When | Effect |
|---|---|---|
| **Stop** | While generating | Cancels immediately; marked "Generation cancelled." |
| **Retry** | After done / cancelled / error | Regenerates that answer using the conversation up to that point |
| **Copy** | As soon as any text exists | Copies the answer text to your clipboard |

### 4.6 Smarter search (automatic query rewriting)

For unscoped and folder-scoped chat, your query is automatically rewritten before searching — helpful for short queries or acronyms that wouldn't match file content well as-is (e.g. `GST` → `GST invoices issued during financial year`). This never blocks search (falls back to your original text if unavailable) and never changes the wording of the final answer, only which files get found.

### 4.7 Grounding & trust

The AI only ever sees the text of the files actually retrieved for your query — no general knowledge, nothing outside your indexed content. If there isn't enough information, the response is exactly:

> "I couldn't find enough information."

with no sources — never a guess. Conversation history lives only in your browser tab; nothing conversational is saved anywhere. Reloading the page starts fresh.

### 4.8 Theme

The sun/moon toggle in the header switches light/dark mode. Your choice is remembered; on your first visit it follows your OS preference.

---

## 5. If something goes wrong

- **No API key configured / AI temporarily unreachable:** the affected message shows a distinct error (not the "couldn't find enough information" text), with a **Retry** option. Search itself (folder browsing, plain retrieval) keeps working regardless — only the AI-generated pieces (answers, rewriting, tags, entities, summaries, AI search suggestions) are affected.
- **Connection drops mid-answer:** the message shows an error alongside whatever partial text had already streamed in, plus Retry.
- **A scan reports failed files:** check the failure list in the scan-complete summary for the specific error per file (e.g. unreadable/corrupt file, OCR unavailable for an image).
