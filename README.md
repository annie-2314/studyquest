# StudyQuest AI

A gamified, multi-agent AI tutoring platform. Explains any concept (text/image/video),
turns YouTube courses into trackable roadmaps, remembers each learner's weak spots, and
gamifies the whole journey. **All 10 build phases are implemented.**

## Architecture
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (`backend/`).
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion + Recharts (`frontend/`).
- **DB:** SQLite for dev (zero install); set `DATABASE_URL` to a Postgres URL for prod — no code change.
- **Auth:** custom JWT (short-lived access token + hashed, rotating, revocable refresh tokens).
- **LLM:** OpenRouter (OpenAI-compatible). One env var `OPENROUTER_API_KEY` powers every agent.
  **Without a key the whole app still runs** in a deterministic mock mode; set the key to go live.
- **Agent frameworks:** LangGraph (stateful supervisor + per-student memory, hard step budget)
  and a role-based Study-Plan crew (Planner → Question-Writer → Reviewer).

## Features by phase
1. Landing page + JWT auth + DB shell.
2. LangGraph supervisor + streaming chat tutor (`/chat`) + per-student memory.
3. Multimodal image solver + basic RAG with citations (`/study`).
4. ⭐ YouTube playlist → trackable roadmap: per-video completion, summaries, transcript Q&A
   (timestamp citations), quizzes with real-life-example fallback (`/courses`).
5. Sandboxed code runner + Code-Review agent (`/code`).
6. Video RAG — YouTube URL or whisper upload → ask with timestamps (`/video`).
7. Gamification — XP, levels, streaks, badges, leaderboard, flashcards, boss quiz (`/arcade`).
8. Study-plan crew + PDF study-guide export (`/plan`).
9. Student + teacher dashboards with progress analytics (`/progress`, `/teacher`).
10. LangSmith tracing (env-gated) + evaluation harness (LLM-as-judge) + citations
    (`/insights`, `python -m scripts.run_eval`).

## API keys (all optional to *run*; required for *real* AI output)
- `OPENROUTER_API_KEY` — the only key needed for live AI across every feature.
- `LANGCHAIN_API_KEY` + `LANGCHAIN_TRACING_V2=true` — optional LangSmith tracing.
- No YouTube API key needed (uses yt-dlp + youtube-transcript-api).

## Notes / environment-driven choices
- RAG uses BM25 (offline, no vector server); swap in Qdrant/pgvector behind `app/rag/store.py`.
- Code sandbox is a timeout-bounded subprocess (best-effort); use Judge0/Docker in production.
- CrewAI itself needs MS C++ Build Tools on Windows (chromadb/hnswlib); the crew runs without it.
- Optional file transcription needs `faster-whisper`; the YouTube-URL path works without it.
- Behind TLS-inspecting proxies, `truststore` + `pip-system-certs` make Python use the OS cert store.
- YouTube ingestion (roadmap/video-RAG) depends on YouTube not rate-limiting/blocking your network;
  on blocked networks transcript fetches return empty and the app shows a graceful "no transcript" message.

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
