# StudyQuest AI

A gamified, multi-agent AI tutoring platform. **Phase 1** delivers a running shell:
an animated landing page, custom-JWT auth, and a SQLite/Postgres-ready database.

## Architecture
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (`backend/`).
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion (`frontend/`).
- **DB:** SQLite for dev (zero install); set `DATABASE_URL` to a Postgres URL for prod — no code change.
- **Auth:** custom JWT (short-lived access token + hashed, rotating, revocable refresh tokens).

Later phases add the LangGraph supervisor + specialist agents, CrewAI study-plan crew,
multimodal learning, YouTube roadmaps, code review, video RAG, gamification, dashboards,
guardrails, and LangSmith tracing. See `docs/superpowers/specs/`.

## Project layout
```
backend/    FastAPI app, models, auth, Alembic migrations, pytest
frontend/   Next.js app (landing page, auth pages, dashboard)
docs/       design spec + implementation plan
docker-compose.yml   optional Postgres for production-parity
```

## Run it locally (no Docker, no paid keys)

### 1. Backend  →  http://localhost:8000  (interactive docs at /docs)
```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (Git Bash):    . .venv/Scripts/activate
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
alembic upgrade head          # creates studyquest.db with users + refresh_tokens
uvicorn app.main:app --reload
```

### 2. Frontend  →  http://localhost:3000
```bash
cd frontend
npm install
cp .env.local.example .env.local   # Windows: copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 → **Start your quest** → sign up → you land on the dashboard.
The full auth round-trip (signup → login → protected dashboard → logout) works end to end.

## Tests
```bash
cd backend && pytest -v        # 13 tests: security, models, deps, auth API, health
```

## Using Postgres instead of SQLite (optional)
```bash
docker compose up -d db
# then in backend/.env:
# DATABASE_URL=postgresql+psycopg://studyquest:studyquest@localhost:5432/studyquest
# (pip install "psycopg[binary]" first)
cd backend && alembic upgrade head
```

## Notes
- All secrets come from environment variables. `.env` / `.env.local` and `*.db` are git-ignored.
- Phase 1 needs **no** API keys. `ANTHROPIC_API_KEY` (pay-as-you-go) is required from Phase 2.
- Fonts load in the browser via `<link>` so the build works on restricted networks (falls back to system fonts).
