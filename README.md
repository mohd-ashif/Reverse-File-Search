# Reverse File Search

AI-powered reverse file search application. Given a query (text, description, or sample content), the system searches previously indexed files and returns the most relevant matches.

Rather than uploading files, users register local folders to monitor. The backend recursively scans each folder, extracts text from supported file types, chunks and embeds the text, and stores the embeddings in a Chroma vector store for semantic search.

**Implemented:** folder registration/scanning (`MonitoredFolder`, `FileScannerService`), text extraction per file type, chunking + embedding pipeline (`IndexingPipeline`), Chroma-backed vector search (`SearchService`).
**Not yet implemented:** auth flows.

## Tech Stack

**Frontend**
- React + Vite
- TailwindCSS
- shadcn/ui
- React Router
- Axios
- Zustand

**Backend**
- FastAPI
- SQLAlchemy (ORM)
- SQLite (database)
- Alembic (migrations)

## Project Structure

```
Reverse File Search/
├── backend/
│   ├── app/
│   │   ├── api/            # HTTP layer (versioned routers, endpoints, deps)
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   ├── core/           # config, security, logging
│   │   ├── db/             # engine/session, declarative base
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # business logic
│   │   ├── repositories/   # data access layer
│   │   ├── utils/          # shared helpers
│   │   └── main.py         # FastAPI app entrypoint
│   ├── alembic/            # migrations
│   ├── storage/            # uploaded files + search index artifacts
│   ├── tests/
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── api/            # axios client + endpoint wrappers
│   │   ├── components/
│   │   │   ├── ui/         # shadcn/ui primitives
│   │   │   ├── layout/     # app shell/layout components
│   │   │   └── common/     # shared components
│   │   ├── features/       # feature modules (search, upload, files)
│   │   ├── hooks/
│   │   ├── lib/            # utils (cn, etc.)
│   │   ├── pages/          # route-level pages
│   │   ├── router/         # React Router config
│   │   ├── store/          # Zustand stores
│   │   ├── styles/         # global css
│   │   └── types/          # shared TS types
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── docs/
├── docker-compose.yml
└── README.md
```

## Backend Architecture

Layered/modular design:

- **api** — routing and request/response handling only, no business logic
- **schemas** — Pydantic models for validation/serialization, decoupled from ORM models
- **services** — business logic, orchestrates repositories
- **repositories** — data access, isolates SQLAlchemy queries from services
- **models** — SQLAlchemy ORM table definitions
- **core** — cross-cutting config, security, logging

Request flow: `endpoint -> service -> repository -> model`

## Database Schema (current)

- **monitored_folders** — id, path, is_active, timestamps
- **indexed_files** — id, folder_id (FK -> monitored_folders), absolute_path, filename, extension, file_type, size_bytes, checksum, mtime, status, error_message, timestamps
- **file_chunks** — id, file_id (FK -> indexed_files), chunk_index, chroma_id, char_count, timestamps

Embeddings themselves live in a Chroma persistent collection (`storage/chroma`), keyed by `chroma_id`; SQL rows track provenance and reconciliation state.

Schema will evolve via Alembic migrations as features are implemented.

## API Structure

Base prefix: `/api/v1`

| Method | Path                     | Description                             |
|--------|--------------------------|------------------------------------------|
| GET    | `/health`                | Service health check                    |
| GET    | `/folders`               | List monitored folders                  |
| POST   | `/folders`               | Register a folder to monitor            |
| DELETE | `/folders/{folder_id}`   | Stop monitoring a folder                |
| POST   | `/folders/{folder_id}/scan` | Scan folder for changes and re-index |
| GET    | `/files`                 | List indexed files                      |
| GET    | `/files/{file_id}`       | Get a single indexed file record        |
| POST   | `/search`                | Reverse file search (embedding-based)   |

## Environment Configuration

See `backend/.env.example` and `frontend/.env.example`. Copy each to `.env` before running.

## Getting Started

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md).
