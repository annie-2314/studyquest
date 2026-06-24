# StudyQuest AI — Phase 1 Design Spec

**Date:** 2026-06-24
**Status:** Approved for implementation
**Scope:** Phase 1 only — "a running, deployable shell." Later phases each get their own spec.

---

## 1. Product context (one line)
An AI tutor that explains any concept (text, image, or video), turns any YouTube
course into a step-by-step trackable roadmap, gamifies learning, remembers each
student's weak spots, and generates personalized study material.

This spec covers **only Phase 1**: project skeleton + interactive landing page +
auth + DB schema + `.env.example` + (optional) docker-compose — a real, runnable shell.

## 2. Confirmed decisions
- **Pacing:** Build Phase 1 to a genuinely working state, stop, checkpoint, then design Phase 2.
- **Auth:** Custom JWT (email/password) implemented entirely in the FastAPI backend. No third-party auth.
- **Credentials:** None required for Phase 1. `ANTHROPIC_API_KEY` (pay-as-you-go, not free) needed from Phase 2. `LANGCHAIN_API_KEY` optional, Phase 10. All wired as `.env.example` placeholders now.
- **Runtime:** Run natively on Windows (no Docker required). docker-compose provided but optional.
- **Dev database:** SQLite for dev (zero install). Postgres-ready: engine selected from a single `DATABASE_URL`, so production swaps with no code change. SQLAlchemy + Alembic.

## 3. Tech stack (Phase 1)
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS + Framer Motion.
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2. JWT via `python-jose`, hashing via `passlib[bcrypt]`, settings via `pydantic-settings`.
- **DB:** SQLite (dev) / Postgres (prod) via `DATABASE_URL`.

## 4. Folder structure
```
tutor/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, routers, exception handlers
│   │   ├── config.py          # pydantic-settings, reads .env
│   │   ├── database.py        # engine + session (SQLite/Postgres via DATABASE_URL)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── user.py        # User, RefreshToken ORM models
│   │   ├── schemas/
│   │   │   ├── auth.py        # signup/login/token DTOs
│   │   │   └── user.py        # user response DTOs
│   │   ├── core/
│   │   │   └── security.py    # bcrypt hashing + JWT create/verify
│   │   └── api/
│   │       ├── deps.py        # get_db, get_current_user
│   │       └── routes/
│   │           ├── auth.py
│   │           └── health.py
│   ├── alembic/               # migrations (+ alembic.ini, env.py)
│   ├── tests/                 # pytest (auth flow)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # landing
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   ├── dashboard/page.tsx # placeholder authed area
│   │   └── globals.css
│   ├── components/
│   │   ├── landing/           # Hero, Features, HowItWorks, DemoPreview, Footer, Nav
│   │   └── ui/                # Button, Input, Card
│   ├── lib/
│   │   ├── api.ts             # typed fetch wrapper
│   │   └── auth.tsx           # auth context + token storage
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── .env.local.example
├── docker-compose.yml         # optional: Postgres + backend + frontend (for later use)
├── .gitignore                 # .env, *.db, node_modules, __pycache__, .next
└── README.md
```

## 5. Database schema

### Implemented in Phase 1
**users**
| column | type | notes |
|---|---|---|
| id | UUID (str) | PK |
| email | str | unique, indexed |
| hashed_password | str | bcrypt |
| display_name | str | |
| role | enum | `student` \| `teacher` \| `parent` (default student) |
| is_active | bool | default true |
| created_at | datetime | |
| updated_at | datetime | |

**refresh_tokens**
| column | type | notes |
|---|---|---|
| id | UUID (str) | PK |
| user_id | UUID (str) | FK → users.id |
| token_hash | str | hashed refresh token |
| expires_at | datetime | |
| revoked | bool | default false (logout / rotation) |
| created_at | datetime | |

### Forward target ERD (documented, NOT built in Phase 1)
These exist only to keep later phases extending cleanly — do not create migrations
for them now (YAGNI):
- `student_profiles`, `weak_spots`, `mastery_topics` (Phase 7/personalization)
- `courses`, `roadmaps`, `roadmap_steps`, `video_steps` (Phase 4)
- `quizzes`, `questions`, `quiz_attempts` (Phase 4)
- `code_submissions`, `code_reviews` (Phase 5)
- `video_uploads`, `transcripts`, `embeddings` (Phase 6 + vector DB)
- `xp_events`, `levels`, `streaks`, `badges`, `user_badges`, `leaderboard` (Phase 7)
- `conversations`, `messages`, `agent_traces` (Phase 2 + memory)

## 6. Auth flow (custom JWT)
Endpoints (all under `/api`):
- `POST /api/auth/signup` → create user (bcrypt hash), return `{access_token, refresh_token, user}`
- `POST /api/auth/login` → verify credentials, return tokens
- `POST /api/auth/refresh` → validate + rotate refresh token, issue new access token
- `POST /api/auth/logout` → revoke the refresh token
- `GET  /api/auth/me` → current authenticated user (protected)
- `GET  /api/health` → liveness check

Details:
- Access token: short-lived JWT (HS256), signed with `SECRET_KEY` from env, ~30 min.
- Refresh token: longer-lived, stored **hashed** in `refresh_tokens`, supports rotation + revocation.
- Passwords hashed with bcrypt; never stored or logged in plaintext.

## 7. Frontend — landing page & auth UI

### Visual identity (deliberately not generic AI-slop)
- **Theme:** RPG / "quest" learning — knowledge as an adventure.
- **Palette:** deep indigo/near-black base (`#0E0B1E`), electric violet + lime/cyan accents (XP energy), warm off-white text.
- **Typography:** Space Grotesk (display/headings) + Inter (body).
- **Motion (Framer Motion):** hero staggered text reveal, floating XP-orb/badge elements, scroll-triggered feature cards, animated progress bar in "How it works."

### Landing sections
1. **Hero** — headline + subhead + "Start your quest" CTA → signup.
2. **Feature showcase** — the 7 specialist agents presented as cards.
3. **How it works** — 3 steps (Pick a course → Follow the roadmap → Level up).
4. **Demo preview** — stylized mock of the roadmap/chat UI (static this phase).
5. **Footer** — links, project tagline.

### Auth pages
- `/signup` and `/login` forms with client-side validation, inline error messages, loading states.
- On success: store access token (memory + refresh via httpOnly-style flow kept simple this phase — access token in context, refresh token in localStorage), redirect to `/dashboard`.
- `/dashboard` is a protected placeholder ("Your quest begins in Phase 2") proving the auth round-trip works end-to-end.

## 8. Cross-cutting concerns (designed now, built in later phases)

### Guardrails (safety) — inserted Phase 2+
Wraps all AI agent I/O. Responsibilities:
- Input moderation + prompt-injection defense (reject instruction-override attempts).
- Output safety: on-topic, age-appropriate, no harmful content.
- PII filtering before anything is written to student memory.
- Code-execution sandboxing (Phase 5): untrusted student code never runs unsandboxed.

Approach: lightweight dependency-free validation layer + Anthropic built-in safety for Phase 2; option to adopt Guardrails AI or NeMo Guardrails for declarative rules later. A clean interface is documented now so insertion is non-invasive. **Not in Phase 1** (no agents yet).

### LangSmith (observability) — Phase 10
Traces every agent step (prompt, tokens, latency, supervisor routing) and supports
LLM-as-judge evals. Optional and env-gated: with `LANGCHAIN_API_KEY` /
`LANGCHAIN_TRACING_V2` unset, the app runs with tracing off. Env placeholders added in Phase 1.

## 9. Error handling
- **Backend:** central exception handler → consistent `{detail, code}` JSON. Explicit handling for 400 (validation), 401 (auth), 409 (duplicate email). No secrets in error bodies.
- **Frontend:** typed API wrapper surfaces non-2xx as inline form errors + toasts; client-side validation; 401 → redirect to login.

## 10. Testing (TDD on the backend)
pytest covering: signup success, duplicate-email 409, login success, wrong-password
401, `/me` with valid token, `/me` without token (401), refresh rotation, logout
revocation. Frontend kept to a smoke check this phase.

## 11. Engineering requirements (from the brief)
- Clean separated frontend/backend folders. ✔ (section 4)
- All keys via env; `.env.example` provided; never hardcoded. ✔
- `.env` + secrets + `*.db` in `.gitignore`. ✔
- Type-safe code (TS strict + Pydantic), clear comments explaining WHY frameworks are used where (matters from Phase 2). ✔
- README: setup, architecture, native-run instructions, per-feature explanation. ✔
- Graceful error handling. ✔ (section 9)
- (Phase 2+) Supervisor step budget to prevent agent infinite loops — documented now.

## 12. Out of scope for Phase 1 (explicit)
LangGraph supervisor, CrewAI crew, any AI/LLM calls, multimodal, YouTube ingestion,
video RAG, code execution, gamification logic, dashboards, vector DB, guardrails
runtime, LangSmith runtime. All deferred to their named phases.

## 13. Definition of done (Phase 1)
- `backend`: `uvicorn app.main:app` runs; Alembic migration creates `users` + `refresh_tokens`; all auth pytest tests pass.
- `frontend`: `npm run dev` serves the animated landing page; signup → login → dashboard round-trip works against the backend.
- README lets a fresh machine run both natively with no paid keys.
