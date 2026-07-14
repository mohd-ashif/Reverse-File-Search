# User Guide — Recent Features

This guide covers two recent additions to Reverse File Search:

1. **Sensitive file protection** during folder scans
2. **AI Answer** — Groq-powered natural-language answers on the Search page

For general setup, see [`INSTALLATION.md`](INSTALLATION.md). For full requirements, see [`SRS.md`](SRS.md).

---

## 1. Sensitive File Protection

When you add or scan a folder, the app automatically checks for files that look like credentials or secrets — for example `.env`, `.pem`, `.key`, `.pfx`, `.kdbx`, `wallet.dat`, `id_rsa`, `credentials.json`, `passwords.txt`.

### When adding a folder

On the **Folders** page, click **Add folder** and enter a path. The preview screen shows an estimate of what will be scanned. If sensitive files are detected, you'll see a red warning banner listing how many and a few examples:

> ⚠ 2 potentially sensitive files detected (e.g. `.env`, `id_rsa`). These look like credentials or keys and are skipped by default when scanning.

This is informational at this step — no files are indexed yet, since adding a folder only registers the path.

### When scanning a folder

Click **Scan** on a monitored folder. If sensitive files are found, a dialog appears with three choices:

| Choice | What happens |
|---|---|
| **Skip sensitive files** (default) | Scan proceeds; sensitive files are never opened, chunked, or embedded. Any previously-indexed sensitive file is also removed. |
| **Continue anyway** | Scan proceeds and sensitive files are indexed like any other supported file. |
| **Cancel** | Nothing happens — no scan runs. |

If no sensitive files are found, scanning proceeds immediately with no dialog.

**Recommendation:** leave the default (Skip) unless you specifically intend to make a credential file searchable.

---

## 2. AI Answer (powered by Groq) — live, streamed

The **Search** page can generate a plain-language answer on top of your search results, instead of just returning raw matching chunks. The answer now streams in live, word by word, like a chat assistant.

### How to use it

1. Go to the **Search** page.
2. Click the **AI Answer** button (top right of the search bar) to turn it on — it highlights when active.
3. Type your query as usual. As soon as you stop typing, the answer card appears and begins generating.

### What you'll see, in order

1. **Thinking…** — a small animated typing indicator appears first, while the request is being set up and before the first word of the answer arrives.
2. **The answer typing itself out** — text appears progressively as the AI generates it, with a blinking cursor at the end while it's still going, exactly like a chat assistant response.
3. **Sources** — badges showing which of your files the answer is based on. These are taken directly from the files search actually retrieved, never invented by the AI, so citations are always real files in your index. They typically appear before the answer text finishes.
4. **Confidence** — a percentage next to "AI Answer" indicating how well your indexed content supports the answer.

### Controls while and after generating

| Button | When it appears | What it does |
|---|---|---|
| **Cancel** | While the answer is being generated | Immediately stops generation. The card shows "Generation cancelled." |
| **Retry** | After the answer finishes, is cancelled, or errors | Re-runs the same query from scratch |
| **Copy** | As soon as any answer text exists (even mid-generation) | Copies the answer text to your clipboard; the button briefly shows "Copied" |

### Grounding rules (why answers are trustworthy)

- The AI is only shown the text of your top retrieved chunks (up to `top_k`, default 10) — it has no access to anything outside your indexed files and no general knowledge is used.
- If your indexed files don't contain enough information to answer the question, the streamed answer will be exactly:

  > "I couldn't find enough information."

  with no sources — the AI will not guess or make something up. This is normal answer text, not an error.

### If something goes wrong

- **No API key configured / AI temporarily unreachable:** the card shows a distinct error message (not the "couldn't find enough information" text) with a **Retry** button. Your regular search results are unaffected either way.
- **Connection drops mid-answer:** the card shows an error with whatever partial answer had already streamed in, plus **Retry**.
- **Nothing matched your query:** the results list is empty and the answer will say it couldn't find enough information, since there's nothing to answer from.

### Regular search still works the same way

When **AI Answer** is off, the list of matching file chunks behaves exactly as before — filename, similarity score, and the matching excerpt — with no AI call and no added latency.
