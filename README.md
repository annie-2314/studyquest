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
  and role-based crews (Planner → Curator → Reviewer).

### Architecture diagram
```mermaid
flowchart LR
  subgraph Client
    UI[Next.js app<br/>chat · learn · materials · roadmap · insights]
  end
  subgraph API[FastAPI backend]
    SUP[LangGraph supervisor<br/>route → respond]
    CREW[Role crews<br/>Planner→Curator→Reviewer]
    RAGG[Grounded RAG<br/>cited answers]
    BKT[Knowledge tracing<br/>Bayesian BKT]
    EVAL[Eval harness<br/>LLM-as-judge]
  end
  subgraph Models[Models / stores]
    LLM[(LLM layer<br/>OpenRouter · Groq · Ollama)]
    EMB[(bge-small embeddings<br/>fastembed/ONNX)]
    VDB[(Vector store<br/>NumPy cosine / pgvector)]
    DB[(SQLAlchemy DB<br/>SQLite / Postgres)]
  end
  UI -- REST + WebSocket --> API
  SUP --> LLM
  CREW --> LLM
  RAGG --> EMB --> VDB
  RAGG --> LLM
  EVAL --> LLM
  BKT --> DB
  API --> DB
  API -. traces .-> OBS[(LangSmith / Langfuse)]
```

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

## Grounded RAG + adaptive learning (engineered upgrade)
Beyond the LLM-knowledge tutor, StudyQuest now grounds answers in the student's own
materials and models what they actually know:

- **Grounded RAG over your materials** (`/materials`): upload a **PDF** (PyMuPDF) or paste
  notes → token-aware chunks (~500 tok, 50 overlap) → embedded **locally and free** with
  **`BAAI/bge-small-en-v1.5` via `fastembed` (ONNX, no PyTorch, no build tools)** → stored
  as vectors in the relational DB. Answers are retrieved by **NumPy cosine** and the tutor
  responds **only from your sources with inline citations** (`from <source>, p.12`); if nothing
  relevant is retrieved it **says so instead of hallucinating**.
  Endpoints: `POST /materials/ingest` (PDF), `POST /materials/ingest/text`, `GET /materials`,
  `POST /materials/ask`.
- **Knowledge tracing (BKT)** — the differentiator: per-concept **Bayesian Knowledge Tracing**
  (`p_init/p_transit/p_slip/p_guess`) exposes mastery `0..1`. Every graded quiz answer updates
  the tagged concept's mastery and a spaced **review schedule**; weak concepts drive adaptation.
  Endpoints: `GET /learning/mastery` (per-concept + over-time history), `GET /learning/review-queue`,
  `POST /learning/attempt`. The **Insights** page visualizes mastery bars + the review queue.

**Free-model stack:** `fastembed` (bge-small, ONNX) for embeddings, `pymupdf` for PDF/figure
extraction, `faster-whisper` (optional) for audio/video transcription — **no paid keys, no
compiler.** The vector store is a clean interface (`app/materials/store.py`) so ChromaDB/Qdrant
can be swapped in later. Everything is mock-runnable: set `EMBEDDINGS_MOCK=1` for a deterministic
hash embedding (used by the test suite, so CI never downloads a model).

- **Multimodal ingestion:** PDF **figures** are extracted (PyMuPDF) and indexed alongside text so
  images are retrievable; set `ENABLE_IMAGE_CAPTIONS=1` (+ transformers/torch) to auto-describe them
  with the free **BLIP** model. A **YouTube/audio URL** can be ingested into the same grounded index
  (`POST /materials/ingest/url` → transcript → chunks).
- **Eval harness (LLM-as-judge):** `POST /eval/factuality` scores how grounded an answer is in its
  sources (catches hallucination); `POST /eval/quiz-validity` checks quiz items. Results persist
  (`eval_results`) and surface in the **Insights** "Recent evaluations" widget.
- **Tracing:** LangSmith (existing) **and** optional **Langfuse** — both env-gated and no-op without
  keys (`app/observability.py`).
- **Local LLM mode:** set `LLM_BACKEND=ollama` to run fully offline against a local **Ollama**
  (e.g. `llama3.1`) via its OpenAI-compatible endpoint; if Ollama isn't reachable it degrades
  gracefully to the mock tutor instead of hanging.

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
