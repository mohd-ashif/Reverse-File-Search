# Installation Guide

## Prerequisites

- Python 3.12+
- Node.js 20+
- npm 10+
- (Optional) Docker + Docker Compose

## 1. Clone & Configure Environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and set a real `SECRET_KEY` before any non-local use.

## 2. Backend Setup (local)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements-dev.txt

# Run initial migration (once models/migrations exist)
alembic upgrade head

uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

## 3. Frontend Setup (local)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api` requests to the backend.

## 4. Running with Docker

From the project root:

```bash
docker compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## 5. Database Migrations

Create a new migration after changing models:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## 6. Running Tests

```bash
cd backend
pytest
```

## Notes

- SQLite database file is created at `backend/storage/app.db` by default.
- Uploaded files are stored under `backend/storage/uploads/`; search index artifacts under `backend/storage/index/`.
- This is a foundation-only setup — upload processing, embedding generation, and search logic are not yet implemented.
