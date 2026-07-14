# User Guide — Recent Features


This guide covers recent additions to Reverse File Search:

1. **Sensitive file protection** during folder scans
2. **Chat** — a full conversational interface, grounded in your indexed files
3. **Smarter search** — your queries are automatically improved before searching

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

## 2. Chat

The **Chat** page (in the nav where "Search" used to be) is a full conversation with an AI grounded in your indexed files — like chatting with an assistant that has only read your files and nothing else.

### Starting a conversation

Open **Chat**. With an empty conversation, you'll see a few **suggested questions** you can click instead of typing — handy for getting a feel for what to ask. Otherwise, just type a question and press **Enter** (Shift+Enter for a new line without sending) or tap the send button.

### What you'll see, in order

1. **Thinking…** — a small animated typing indicator while the request is being set up, before the first word arrives.
2. **The answer typing itself out** — text appears progressively with a blinking cursor while it's still generating, formatted as proper **Markdown**: headings, lists, tables, and **code blocks** all render properly. Each code block has its own **Copy** button and shows its language if one was specified.
3. **A "Searched for: ..." note**, if your query was rephrased for a better search match — see §3 below.
4. **Sources** — clickable badges naming the files the answer is based on. Clicking one that matches an indexed file opens that file's detail view. These come directly from the files actually retrieved, never invented by the AI.
5. **Confidence** — a percentage under the answer, indicating how well your indexed content supports it.

### Conversation history

Chat remembers your conversation — you can ask a follow-up like "what about the other one?" and it will understand what you mean from the earlier turns. This history is **not saved anywhere** — it lives only in your browser tab for the current session; reloading the page starts a fresh conversation.

### Controls on each message

| Button | When it appears | What it does |
|---|---|---|
| **Stop** (input bar) | While a response is being generated | Immediately stops generation for that message. It's marked "Generation cancelled." |
| **Retry** | After a message finishes, is cancelled, or errors | Regenerates just that answer, using the conversation up to that point |
| **Copy** | As soon as any answer text exists (even mid-generation) | Copies that message's answer text to your clipboard |

### Grounding rules (why answers are trustworthy)

- The AI is only shown the text of your top retrieved chunks — it has no access to anything outside your indexed files and no general knowledge is used.
- If your indexed files don't contain enough information to answer, the response will be exactly:

  > "I couldn't find enough information."

  with no sources — the AI will not guess or make something up. This is normal answer text, not an error.

### If something goes wrong

- **No API key configured / AI temporarily unreachable:** that message shows a distinct error (not the "couldn't find enough information" text) with a **Retry** option.
- **Connection drops mid-answer:** the message shows an error alongside whatever partial answer had already streamed in, plus **Retry**.

### Light / dark mode

Use the sun/moon button in the top-right of the header to switch themes. Your choice is remembered for next time; on your very first visit it follows your operating system's theme.

---

## 3. Smarter search (automatic query rewriting)

Before searching your files, your query is automatically improved to get better matches — especially useful for short queries, acronyms, or abbreviations that wouldn't match file content well on their own.

**Example:**

| You type | The app actually searches for |
|---|---|
| `GST` | `GST invoices issued during financial year` |

When this happens, you'll see a small note under the answer: *"Searched for: “...”"* — so you always know what was actually matched against your files, even though you get to keep typing short and natural.

This step never blocks your search: if it's unavailable for any reason, your original query is used as-is, exactly like before. It also never changes what the AI's final answer is about — it only affects which files get found, not how the answer is worded.
