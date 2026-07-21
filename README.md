# Reverse File Search

AI-powered reverse file search application. Instead of searching by filename, you register local folders to monitor; the system extracts, chunks, and embeds their content, then lets you find and converse with that content using natural-language queries.

Rather than uploading files, users register local folders to monitor. The backend recursively scans each folder, extracts text from supported file types, chunks and embeds the text, and stores the embeddings in a Chroma vector store for semantic search. Beyond search, the system also automatically classifies documents into categories, extracts structured business fields, generates on-demand summaries, and provides an AI chat interface — globally, scoped to a folder, or scoped to a single file.

**Implemented:**
- Folder registration/scanning (`MonitoredFolder`, `FileScannerService`), synchronous or as a background job with live WebSocket progress.
- Sensitive-file detection (credentials/keys), skipped from indexing by default.
- Text extraction per file type (PDF, DOCX, TXT, Markdown, Excel, image OCR), chunking + embedding pipeline (`IndexingPipeline`), Chroma-backed vector search (`SearchService`).
- Automatic document classification into category tags (Invoice, Contract, Resume, Tax, Purchase Order, Medical Record, Salary Slip, Bank Statement, Receipt, Letter, or custom), shown as colored icon badges, filterable.
- Structured entity extraction (invoice number, vendor, GST/PAN, amount, date, contact details, etc.).
- On-demand structured document summaries.
- Groq-backed query rewriting, AI-generated grounded answers (streaming + non-streaming), and search-box autocomplete (recent/popular/AI-generated suggestions).
- Multi-turn AI chat, unscoped, folder-scoped, or single-file-scoped, with isolated conversation memory per scope and source citations.

**Not yet implemented:** authentication/authorization enforcement; per-user data isolation.

## Documentation

| Document | Covers |
|---|---|
| [`docs/SRS.md`](docs/SRS.md) | Full functional & non-functional requirements |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System design, service map, data model, indexing/search pipelines |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Complete REST/SSE/WebSocket API reference |
| [`docs/INSTALLATION.md`](docs/INSTALLATION.md) | Setup, local dev, Docker, migrations, tests |
| [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) | End-to-end walkthrough of every feature |

## Tech Stack

**Frontend**
- React + Vite + TypeScript
- TailwindCSS + shadcn/ui
- React Router
- TanStack Query (server state)
- Axios

**Backend**
- FastAPI + Uvicorn
- SQLAlchemy (ORM) + Alembic (migrations)
- PostgreSQL (relational metadata)
- ChromaDB (persistent vector store)
- sentence-transformers (embeddings)
- Groq Cloud (optional LLM backend for query rewriting, AI answers, tagging, entity extraction, summaries, search suggestions)

## Project Structure

```
Reverse File Search/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # health, folders, files, search, ws
│   │   ├── core/               # config, logging
│   │   ├── db/                 # engine/session, declarative base
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # business logic
│   │   ├── repositories/       # data access layer
│   │   └── main.py             # FastAPI app entrypoint
│   ├── alembic/                # migrations
│   ├── storage/                # Chroma persistent vector store
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                # axios client + endpoint wrappers
│   │   ├── components/         # ui primitives, layout, shared
│   │   ├── features/           # folders, files, chat feature modules
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── router/
│   │   └── types/
│   └── package.json
├── docker/                     # backend.Dockerfile, frontend.Dockerfile
├── docs/                       # SRS, architecture, API reference, guides
└── docker-compose.yml
```

## Getting Started

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md).
