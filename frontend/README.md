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

### Search
`SearchPage` posts a free-text query and renders ranked chunk matches with their source file. Toggling **AI Answer** switches to a live-streamed, ChatGPT-like answer experience:

- `useStreamingAnswer` (`src/hooks/useStreamingAnswer.ts`) opens a `fetch` request to `POST /search/stream`, parses the `text/event-stream` body with `parseSseStream` (`src/lib/sse.ts`), and exposes a single state object (`status`, streamed `results`, accumulated `text`, `sources`, `confidence`, `errorMessage`).
- `AIAnswerPanel` (`src/features/search/AIAnswerPanel.tsx`) renders that state: a typing indicator before the first token, tokens appended live as they arrive, a blinking cursor while streaming, **Sources** badges and a **Confidence** percentage once available, and a distinct error message if generation fails (separate from the model's own "I couldn't find enough information" response, which is normal answer text, not an error).
- **Cancel** aborts the in-flight request (`AbortController`) — the panel shows "Generation cancelled." and offers **Retry**.
- **Retry** re-runs the last query; available after the answer completes, errors, or is cancelled.
- **Copy** copies the answer text to the clipboard (available as soon as there's any text, even mid-stream), with a brief "Copied" confirmation.

When AI Answer is off, `SearchPage` falls back to the plain, non-streaming `POST /search/` call as before — no LLM overhead unless the user opts in.

### Files
`FilesPage` lists indexed files (optionally filtered by folder) and opens `FileDetailDialog` for a single file's metadata/status.

## Testing

```bash
npm test
```

Unit tests currently cover folder path risk classification (`src/lib/folderRisk.test.ts`).
