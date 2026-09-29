# XAI-ResOpt

XAI-ResOpt is an explainable, evidence-backed resume evaluation and optimization platform. This repository currently contains **Phase 1: Project Foundation** only.

## Prerequisites

- Docker Desktop with Docker Compose
- Node.js 22 or newer and npm
- Python 3.11 or newer

## Environment

Copy `.env.example` to `.env` and adjust local values if needed. Do not commit real credentials.

## Start Local Services

```powershell
Copy-Item .env.example .env
docker compose up --build postgres redis backend frontend
```

The frontend is available at `http://localhost:3000`. The backend health endpoint is `http://localhost:8000/api/health`.

## Run Services Individually

Start infrastructure:

```powershell
docker compose up -d postgres redis
```

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Frontend:

```powershell
Set-Location frontend
npm install
npm run dev
```

## Foundation Checks

The status view calls the backend and reports real PostgreSQL and Redis connectivity. A degraded result is not mocked as success.

```powershell
Invoke-RestMethod http://localhost:8000/api/health
python -m pytest backend\tests -q
Set-Location frontend
npm run typecheck
npm run build
```

## Database and Authentication

The database schema is managed with Alembic. After PostgreSQL and Redis are running, apply migrations from the backend directory:

```powershell
Set-Location backend
$env:PYTHONPATH = "."
python -m alembic upgrade head
```

Authentication endpoints are `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, and protected `GET /api/me`. Set a strong `JWT_SECRET` in `.env` for anything beyond local development. Auth integration tests require reachable PostgreSQL and Redis and skip explicitly when either dependency is unavailable.

Document ingestion endpoints are protected by the same bearer token: `POST /api/ingestion/resumes`, `POST /api/ingestion/job-descriptions`, and `POST /api/ingestion/external`. They perform deterministic PDF/DOCX/text extraction, provenance capture, upload validation, and SSRF-aware public URL fetching. No LLM, agent, RAG, scoring, or optimization logic is used in this phase.

## Scope

This phase intentionally does not implement resume/JD parsing, RAG, agents, scoring, optimization, Copilot, integrations, or resume generation. Those are sequenced in [docs/IMPLEMENTATION-PLAN.md](docs/IMPLEMENTATION-PLAN.md).
