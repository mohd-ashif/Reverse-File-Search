# Reverse File Search — Frontend

React + Vite single-page app for the Reverse File Search application. Lets users register folders to monitor, trigger scans/indexing, browse indexed files, and chat with an AI grounded in their content.

See the [root README](../README.md) for the overall project overview and the [SRS](../docs/SRS.md) for full requirements.

## Tech Stack

- **React 18** + **Vite** — app shell and dev server/build tool
- **TypeScript**
- **TailwindCSS** + **shadcn/ui** (Radix primitives) — styling and accessible UI components
- **React Router** — client-side routing
- **TanStack Query** — server-state fetching/caching/mutations
- **Axios** — HTTP client
- **React Hook Form + Zod** — form state and validation
- **Zustand** — local/client state (where needed beyond server state)
- **Vitest** — unit tests
- **sonner** — toast notifications
- **react-markdown** + **remark-gfm** + **@tailwindcss/typography** — Markdown/GFM rendering (tables, code blocks) in chat answers

## Project Structure

```
frontend/
├── src/
│   ├── api/            # axios client + endpoint wrappers (folders, files)
│   ├── components/
│   │   ├── ui/          # shadcn/ui primitives (button, dialog, alert-dialog, textarea, ...)
│   │   ├── layout/       # app shell/layout components (incl. ThemeToggle)
│   │   └── common/       # shared components (MarkdownContent, TypingIndicator)
│   ├── features/         # feature modules
│   │   ├── folders/       # add/list/scan/remove monitored folders, risk + sensitive-file warnings
│   │   ├── files/          # indexed file detail views
│   │   ├── chat/            # chat UI: message bubbles, input, suggested questions, source citations
│   │   └── onboarding/      # first-run guidance
│   ├── hooks/             # TanStack Query hooks (useFolders, useFiles, ...), useDebounce, useChat, useTheme
│   ├── lib/                # utils (cn, folder path risk classification, status formatting, SSE parsing)
│   ├── pages/               # route-level pages (Home, Folders, Chat, Files, NotFound)
│   ├── router/               # React Router config
│   ├── store/                 # Zustand stores
│   ├── styles/                 # global css
│   └── types/                  # shared TS types (folder, scan, search, chat, file)
├── index.html
├── package.json
├── vite.config.ts
├── components.json           # shadcn/ui config
└── postcss.config.js
```

## Prerequisites

- Node.js 20+
- npm 10+
- The backend running locally (see `../backend/README.md`) — the dev server proxies `/api` to it

## Setup

```bash
cd frontend
npm install

cp .env.example .env
```

## Running

```bash
npm run dev
```

- App: `http://localhost:5173`
- Requests to `/api/*` are proxied to `http://localhost:8000` (see `vite.config.ts`); in production, point `VITE_API_BASE_URL` at the deployed backend instead.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Base URL the API client (`src/api/client.ts`) prefixes all requests with |

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite dev server with hot reload |
| `npm run build` | Type-check (`tsc -b`) and produce a production build |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run ESLint |
| `npm test` | Run the Vitest suite |

## Routes

| Path | Page | Purpose |
|---|---|---|
| `/` | `HomePage` | Landing / overview |
| `/folders` | `FoldersPage` | Register, estimate, scan, and remove monitored folders |
| `/search` | `ChatPage` | Chat with an AI grounded in your indexed files (route path kept as `/search` for URL stability; the nav label is "Chat") |
| `/files` | `FilesPage` | Browse indexed files and their status |
| `*` | `NotFoundPage` | Fallback for unmatched routes |

## Key Features

### Add a folder
`AddFolderDialog` takes a filesystem path, classifies its risk (`lib/folderRisk.ts` — flags overly broad paths like drive roots), then calls `POST /folders/estimate` to preview file counts, estimated size/time, large-file warnings, and sensitive-file warnings (`FolderEstimatePreview`) before the folder is actually registered.

### Scan a folder
`FolderRowActions` triggers `POST /folders/{id}/scan`. Before scanning, it re-runs the estimate check; if potentially sensitive files (credentials, private keys, `.env` files, etc.) are detected, a confirmation dialog is shown with three choices:

- **Skip sensitive files** (default) — scan proceeds, sensitive files are excluded from indexing
- **Continue anyway** — scan proceeds and sensitive files are indexed too
- **Cancel** — no scan is performed

### Chat
`ChatPage` (`src/pages/ChatPage.tsx`) is a full conversational interface over `POST /search/stream`, built from components under `src/features/chat/`:

- **`useChat`** (`src/hooks/useChat.ts`) — the core hook. Holds the conversation as an array of `ChatTurn`s (`src/types/chat.ts`), sends each new message with a trimmed `history` of prior turns (last 20 messages, assistant turns only once `status: "done"`), and streams the response into the corresponding assistant turn via `parseSseStream` (`src/lib/sse.ts`). Exposes `sendMessage`, `retryTurn`, `cancel`, and `clear`.
- **`ChatMessageBubble`** — renders one turn: user messages as plain-text bubbles; assistant messages via `MarkdownContent`, with a typing indicator before the first token and a blinking cursor while streaming. Per-message **Retry** (regenerates that answer using the conversation up to that point) and **Copy** actions, a **Confidence** percentage, and — once the backend's query-rewrite step reports one — a small "Searched for: ..." caption showing the query that was actually embedded for retrieval (see backend README's "Query rewriting" section).
- **`MarkdownContent`** (`src/components/common/MarkdownContent.tsx`) — renders full Markdown/GFM (tables, lists, etc.) via `react-markdown` + `remark-gfm`, styled with `@tailwindcss/typography`. Fenced code blocks get a language label and their own **Copy** button; links open in a new tab.
- **`SourceCitations`** — renders each answer's cited filenames as badges; clicking one that resolves to a known file opens the existing `FileDetailDialog` (matched from the retrieved chunks' `file_id`, not from the model's output).
- **`SuggestedQuestions`** — shown when the conversation is empty, offering a few starter prompts.
- **`ChatInput`** — auto-resizing textarea; Enter sends, Shift+Enter inserts a newline; swaps to a Stop button while a response is streaming.
- Auto-scroll: the message list scrolls to the bottom as new content arrives, unless the user has manually scrolled up more than ~80px from the bottom — scrolling back down re-enables it.
- **Cancel** aborts the in-flight request; the turn is marked "Generation cancelled." and can be retried.

### Dark mode
`useTheme` (`src/hooks/useTheme.ts`) toggles Tailwind's class-based dark mode (`darkMode: ["class"]`) on `document.documentElement`, persisted to `localStorage` and defaulting to the OS preference on first visit. `ThemeToggle` (`src/components/layout/ThemeToggle.tsx`) sits in the app header.

### Files
`FilesPage` lists indexed files (optionally filtered by folder) and opens `FileDetailDialog` for a single file's metadata/status.

## Testing

```bash
npm test
```

Unit tests currently cover folder path risk classification (`src/lib/folderRisk.test.ts`).
