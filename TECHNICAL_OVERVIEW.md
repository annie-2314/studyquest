# StudyQuest AI — Technical Overview

A gamified, multi-agent AI tutoring platform that grounds answers in the student's
own materials, models what they actually know (knowledge tracing), and turns any
topic / YouTube course / goal into a structured, trackable learning experience.

This document explains, technically, **everything that's built**, **what library/tech
powers each piece**, and **which model is used for each task**.

---

## 1. Architecture at a glance

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router) · TypeScript · Tailwind CSS · Framer Motion · Recharts · react-markdown + remark-gfm |
| **Backend** | FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · Uvicorn (+ WebSockets) |
| **Database** | SQLite (dev, zero-install) / PostgreSQL (prod via `psycopg2-binary`) — switch with `DATABASE_URL`, no code change |
| **Auth** | Custom JWT — short-lived access token + hashed, rotating, revocable refresh tokens (`python-jose`, `passlib`/`bcrypt`) |
| **LLM access** | OpenRouter (OpenAI-compatible) **or** local Ollama — one shared layer, selectable via `LLM_BACKEND` |
| **Agent orchestration** | LangGraph (stateful supervisor) + role-based "crews" (Planner→Curator→Reviewer) |
| **Embeddings / RAG** | `fastembed` (BAAI/bge-small-en-v1.5, ONNX) + NumPy cosine; plus a BM25 store (`rank-bm25`) |
| **Multimodal** | PyMuPDF (PDF text + figures), faster-whisper (audio/video, optional), BLIP captioning (optional) |
| **Observability** | LangSmith **and** Langfuse tracing (both env-gated, no-op without keys) |

**Design principle:** the whole app is **mock-runnable with zero API keys** — every
LLM call falls back to a deterministic mock, and embeddings fall back to a deterministic
hash vector (`EMBEDDINGS_MOCK=1`), so the test suite never makes a paid call or downloads a model.

---

## 2. The LLM layer (`app/agents/llm.py`)

A single access layer powers every agent. It exposes two **tiers**:

- **FAST** — cheap, high-volume text (chat, summaries, quizzes, explanations).
- **SMART** — harder reasoning / vision (image solver, quiz authoring, grading, judging).

It supports two **backends**, chosen by `LLM_BACKEND`:

| Backend | How it connects | Models (configurable via env) |
|---------|-----------------|-------------------------------|
| `openrouter` (default) | `ChatOpenAI(base_url=OpenRouter)` | FAST = `deepseek/deepseek-chat`, SMART = `openai/gpt-4o-mini` |
| `ollama` | `ChatOpenAI(base_url=http://localhost:11434/v1)` | FAST/SMART = `llama3.1` (local, free) |

- Models are **cached** per `(backend, tier, temperature, model)`.
- Ollama has a **reachability probe** — if it's offline, the layer returns `None` and the
  app degrades gracefully to the mock tutor instead of hanging.
- Because it's all OpenAI-compatible, the same code runs against OpenRouter, Gemini's
  OpenAI endpoint, Groq, or Ollama by changing only env vars.

---

## 3. Which model is used where

> "FAST" / "SMART" map to the configured OpenRouter (or Ollama) slugs above.
> Pure-Python items use **no LLM** at all.

| Feature / task | Model / tier | Library |
|----------------|--------------|---------|
| **Chat tutor** (streaming) | FAST | LangGraph + LangChain |
| Concept-explainer & other chat specialists | FAST | LangChain |
| **Learn** — Summarize | FAST | LangChain |
| **Learn** — Explain (interest-tailored / code snippet) | FAST | LangChain |
| **Learn** — Flashcards | SMART | LangChain |
| **Learn** — Quiz (boss) | SMART | LangChain |
| **Courses** — video summary | FAST | LangChain |
| **Courses** — quiz generation | FAST | LangChain |
| **Courses** — answer grading | SMART | LangChain |
| **Courses** — transcript Q&A | SMART | LangChain |
| **Roadmap** — Planner (the phases) | SMART | role-crew on LangChain |
| **Roadmap** — Reviewer (the note) | FAST | role-crew on LangChain |
| **Roadmap** — Resource curation (YouTube links) | *none* | pure Python (URL building) |
| **Image solver** (photo → solution) | SMART (vision) | LangChain (multimodal message) |
| **BM25 RAG** answer (`/study`, `/video`) | SMART | `rank-bm25` + LangChain |
| **Grounded RAG** answer (`/materials`) | FAST | fastembed + NumPy + LangChain |
| **Embeddings** (grounded RAG) | `BAAI/bge-small-en-v1.5` | `fastembed` (ONNX) |
| **Transcription** (YouTube) | *none (caption API)* | `youtube-transcript-api` |
| **Transcription** (uploaded file) | Whisper **"base"** | `faster-whisper` (optional, local) |
| **PDF figure captioning** | `Salesforce/blip-image-captioning-base` | `transformers` (optional, opt-in) |
| **Knowledge tracing** (mastery) | *none* | pure-Python BKT |
| **Eval** — explanation quality | SMART | LLM-as-judge |
| **Eval** — factuality / grounding | SMART | LLM-as-judge |
| **Eval** — quiz validity | SMART | LLM-as-judge |
| **PDF export** | *none* | `fpdf2` |
| **Code sandbox** | *none* | subprocess (timeout-bounded) |

---

## 4. Agent orchestration

### 4.1 LangGraph supervisor (`app/agents/supervisor.py`)
The chat tutor is a **stateful `StateGraph`**: `START → supervisor (route) → respond → END`.
- `classify_route()` does deterministic keyword routing to a specialist (concept-explainer,
  practice-question, progress-tracker, …) — testable and free.
- A hard **`STEP_BUDGET = 6`** prevents infinite agent loops.
- The REST path runs the compiled graph; the **WebSocket** path reuses the same routing +
  prompt-building to **stream tokens** live, then persists the turn and updates per-student memory.

### 4.2 Role-based crews (`app/crew/…`)
CrewAI itself needs MS C++ Build Tools (chromadb/hnswlib) and won't build on Windows, so the
**same role-pipeline pattern** is implemented on the shared LLM layer:
- **Study-Plan crew:** Planner → Question-Writer → Reviewer.
- **Roadmap crew:** Planner → Resource-Curator → Reviewer (`app/crew/roadmap.py`).

---

## 5. Feature-by-feature

### 5.1 Auth & accounts
JWT access token (~30 min) + a **hashed, rotating, revocable refresh token** (~7 days).
Frontend `apiFetch` transparently refreshes on a 401 and retries once.

### 5.2 Chat Tutor (`/chat`)
LangGraph supervisor, **token streaming over WebSocket**, per-student memory threaded into
each turn, conversations + messages persisted. Frontend restores the last conversation on
return and offers "New chat". Renders Markdown.

### 5.3 Learn (`/arcade`)
The "understand anything" hub. Pick a **topic**, an **uploaded source**, or **paste a web URL**:
- **Summarize** — "what this is" + key points (FAST).
- **Explain** — in-depth, with a real-life example **tailored to the learner's stated interest**,
  or a small **W3Schools-style code snippet** for programming concepts (FAST).
- **Flashcards** + **Quiz me** — generated from the chosen material (SMART), with instant
  green/red feedback, running score, and an **Explain** button per question.
- Slim XP/level strip + achievements + leaderboard (gamification kept secondary).
- Web-URL ingestion: `app/web_ingest.py` fetches the page (httpx), strips HTML, indexes it.

### 5.4 My Materials — Grounded RAG (`/materials`) ⭐
The engineered differentiator. **Answers come only from the student's own sources, with citations.**
- **Ingest:** PDF (PyMuPDF) or pasted text → **token-aware chunks** (~500 tokens, 50 overlap)
  → embedded with **bge-small (fastembed/ONNX)** → stored as JSON-vector rows.
- **Retrieve:** `embed_query` → **NumPy cosine** top-k (scoped to one material or all).
- **Answer:** the LLM (FAST) is instructed to use **only** the retrieved chunks and cite them
  inline (`from <source>, p.12`); if nothing relevant is retrieved it **says so** instead of
  hallucinating (a low cosine backstop + the prompt's "say if absent" rule).
- **Endpoints:** `POST /materials/ingest` (PDF), `/materials/ingest/text`, `/materials/ingest/url`
  (YouTube transcript), `GET /materials`, `POST /materials/ask`.

### 5.5 Knowledge Tracing / Mastery (`/learning`) ⭐
Per-concept **Bayesian Knowledge Tracing** (`app/learning/bkt.py`), params
`{p_init, p_transit, p_slip, p_guess}`, mastery exposed as `p_known ∈ [0,1]`:
- Every graded quiz answer (Courses server-side grade, and the Learn quiz) calls
  `record_attempt` → Bayesian update → persisted in `learner_concept_mastery`, with a
  time-series in `mastery_events`.
- **Spaced review:** `due_at` interval grows with mastery; `GET /learning/review-queue`
  returns due/weakest-first concepts to drive adaptation.
- **Endpoints:** `GET /learning/mastery` (per-concept + history), `GET /learning/review-queue`,
  `POST /learning/attempt`. Visualized on **Insights** (mastery bars + review queue).

### 5.6 Roadmap (`/plan`)
Goal-based learning path generator. Input: **goal + hours/week + timeline + language**.
The crew (SMART planner + FAST reviewer) returns ordered, time-boxed **phases** with topics
and **clickable YouTube search links** (built in pure code — no API key, never blocked).
Roadmaps are **persisted** (`roadmaps` table), listed, reopenable, deletable, and exportable
to **PDF** (`fpdf2`).

### 5.7 Courses (`/courses`)
Paste a **YouTube playlist** → trackable course. Per video: completion, summary (FAST), transcript
Q&A with timestamp citations (SMART), quiz (FAST) + grading (SMART) that **feeds the mastery engine**.
Uses `yt-dlp` + `youtube-transcript-api` (no YouTube API key). An offline **demo course** path
exists for networks where YouTube is blocked.

### 5.8 Study Tools (`/study`)
- **Image solver:** upload a photo of a problem → SMART vision model returns a worked solution.
- **BM25 knowledge base:** paste notes → chunked + indexed with `rank-bm25` → grounded, cited Q&A.

### 5.9 Video RAG (`/video`)
YouTube URL **or** uploaded file → transcript → timestamped chunks → ask with `[mm:ss]` citations.
File transcription uses **faster-whisper** (optional, local, free); YouTube uses the caption API.

### 5.10 Code Playground (`/code`)
In-browser editor → **sandboxed subprocess** run (timeout + output cap) → **Code-Review agent**
verdict. A PASS marks the related course step complete and awards a badge.

### 5.11 Gamification
XP, levels, streaks, badges, leaderboard (`app/gamification/`). XP is awarded for step completion,
quiz passes, code-review passes, and mini-games (per-call XP capped to prevent farming).

### 5.12 Insights & Eval (`/insights`)
- **Concept mastery** bars + **review queue** (from the BKT engine).
- **LangSmith tracing** status + an **in-app trace viewer** (recent runs via the LangSmith SDK:
  step, status, latency, tokens).
- **LLM-as-judge** widgets: explanation quality, plus persisted **factuality** (grounded vs
  hallucinated) and **quiz-validity** scores (`eval_results`), shown in "Recent evaluations".
- **Quiz improvement** trend (first-half vs second-half pass rate).

---

## 6. Eval harness & tracing (`app/eval/`, `app/observability.py`)

- **LLM-as-judge** (`judge_explanation`, `judge_factuality`, `judge_quiz_validity`): each returns a
  score + rationale; mock-safe heuristics when no key (e.g. factuality falls back to lexical overlap).
- **Factuality** specifically scores how grounded an answer is in the provided source chunks —
  this is the hallucination detector. Results persist to `eval_results`.
- **Tracing:** LangSmith (auto-instruments LangChain/LangGraph when `LANGCHAIN_*` set) and
  **Langfuse** (callback handler, wired into the grounded path). Both **no-op without keys**.

---

## 7. Data model & migrations

SQLAlchemy models, created idempotently on startup **and** managed by **Alembic** (`0001`→`0007`,
non-destructive):

| Table | Purpose |
|-------|---------|
| `users`, `refresh_tokens` | auth |
| `conversations`, `messages`, `student_memory` | chat + per-student memory |
| `documents`, `doc_chunks` | BM25 RAG store |
| `courses`, `course_steps` | YouTube-playlist courses |
| `game_profiles`, `user_badges` | gamification |
| `roadmaps` | saved goal-based roadmaps (JSON) |
| `materials`, `material_chunks` | grounded-RAG sources + embedded chunks |
| `learner_concept_mastery`, `mastery_events` | BKT mastery state + history |
| `eval_results` | persisted LLM-as-judge evaluations |

---

## 8. Free-model / zero-key stack

| Capability | Free model / tool | Cost |
|------------|-------------------|------|
| Text generation | OpenRouter `deepseek/deepseek-chat` (≈ free) **or** local Ollama `llama3.1` | ~$0 |
| Embeddings | `BAAI/bge-small-en-v1.5` via fastembed (ONNX, local) | $0 |
| YouTube transcripts | `youtube-transcript-api` | $0 |
| Audio/video transcription | `faster-whisper` (local, optional) | $0 |
| PDF figure captions | `Salesforce/blip-image-captioning-base` (local, optional) | $0 |
| Knowledge tracing, BM25, PDF export, sandbox | pure Python | $0 |

No build tools required for the core (fastembed/pymupdf ship wheels). Heavy optionals
(faster-whisper, BLIP/torch) are lazy-imported and gated, so they never block the base app.

---

## 9. Testing & verification

- **pytest** suite (66 tests) runs entirely in **mock mode** — `OPENROUTER_API_KEY=""` forces the
  mock LLM and `EMBEDDINGS_MOCK=1` forces hash embeddings, so CI makes **no paid calls and no model
  downloads**. Covers: auth, chat graph, study/RAG, courses, code sandbox, video, gamification,
  roadmap (persist/list/get/delete), eval (factuality grounded-vs-hallucinated, quiz validity),
  BKT update logic, and the grounded retrieval/citation + not-found path.
- **Frontend:** `tsc --noEmit` clean.
- **Migrations:** `alembic upgrade head` applies `0001→0007` on a fresh DB.

---

## 10. Deployment

- **Render** (Blueprint `render.yaml`) deploys both services on the free plan; backend supports the
  WebSocket the chat tutor needs. Frontend can alternatively go on Vercel.
- **DB:** free **Neon/Supabase Postgres** for persistence (Render's free disk is ephemeral).
- Tables auto-create on first boot, so a fresh cloud DB works immediately.
- **Known free-tier realities:** services cold-start after idle; YouTube features may be blocked
  from datacenter IPs (use file upload / pasted text instead).

---

# 11. How to explain this project in an interview (start → end)

This is a narrative walkthrough — roughly the order I'd speak it. Use the short version
for a screen, expand the deep-dives when they probe.

## 11.1 The 30-second pitch
> "StudyQuest is an AI tutor, but the interesting part isn't the chat — it's two things most
> 'GPT-wrapper' projects skip. **One**, answers are **grounded in the student's own uploaded
> material with citations**, and it refuses to answer when the material doesn't cover the question,
> so it doesn't hallucinate. **Two**, it **models what the student actually knows** with Bayesian
> Knowledge Tracing and adapts practice to weak concepts. Around that I built a multi-agent backend
> on LangGraph, an LLM-as-judge eval harness, tracing, and a pluggable model layer that runs on
> OpenRouter, Groq, or a fully-local Ollama — so the whole thing can run on free, open-source models."

## 11.2 The problem I set out to solve
Generic AI tutors have two weaknesses: they **hallucinate** (state confident wrong facts), and they
are **not personalized** (they don't track mastery, so every learner gets the same flow). I designed
the system specifically to attack those two — grounding solves hallucination, knowledge tracing
solves personalization.

## 11.3 The stack, and *why* each choice
- **FastAPI** backend — async, first-class **WebSockets** (needed for token streaming), auto Swagger.
- **Next.js (App Router)** frontend — server components + a clean client for the streaming chat.
- **SQLAlchemy 2.0 + Alembic** — one ORM, **SQLite for zero-setup dev, Postgres for prod**, switched by
  a single `DATABASE_URL`; Alembic for non-destructive migrations.
- **Custom JWT auth** — short-lived access token + a **hashed, rotating, revocable refresh token**, so a
  leaked refresh token can be revoked and isn't stored in plaintext.
- **A single LLM access layer** — every agent goes through `app/agents/llm.py`, which exposes a FAST and a
  SMART tier and can point at OpenRouter / Groq / Ollama. This abstraction is why switching providers is a
  config change, not a code change.

## 11.4 Walk the request lifecycle (the chat tutor)
> "When a student sends a chat message, it goes over a **WebSocket** to FastAPI. A **LangGraph state
> graph** runs: a `supervisor` node classifies intent and routes to a specialist, then a `respond` node
> streams tokens back. The graph has a **hard step budget** so an agent can never loop forever. Each turn
> is persisted, and a per-student memory summary is threaded into the next turn's prompt. I deliberately
> kept routing rule-based so it's deterministic and free to test."

## 11.5 Deep dive #1 — Grounded RAG with citations (the anti-hallucination part)
> "Ingestion: a PDF is parsed with **PyMuPDF**, chunked **token-aware** (~500 tokens, 50 overlap so a
> concept spanning a boundary is still retrievable), each chunk embedded with **bge-small** via
> **fastembed** — that's an **ONNX** model, so embeddings run **locally and free with no PyTorch and no
> compiler**. At query time I embed the question and take the **top-k by cosine similarity**. The LLM is
> prompted to answer **only** from those chunks and cite them inline; if the best similarity is below a
> floor, it says 'I can't find this in your materials' instead of guessing.
>
> I started with a **NumPy cosine** store (zero-ops, runs on SQLite), and put it behind a `search()`
> interface so I could later drop in **pgvector** — which I did: flip `VECTOR_BACKEND=pgvector` and the
> embedding column becomes a real `vector(384)` and search is pushed to Postgres with the `<=>` operator.
> The interface meant that swap touched almost no calling code."

**Likely probe — "how do you stop hallucination?"** Two layers: a retrieval-score floor that catches the
"nothing relevant" case, and a prompt that forces source-only answers + an explicit refusal instruction;
plus an offline **factuality judge** that scores how grounded each answer is.

## 11.6 Deep dive #2 — Knowledge tracing (the personalization part)
> "I model mastery per concept with **Bayesian Knowledge Tracing** — four parameters: prior, learn-rate,
> slip, guess. Each graded answer applies Bayes to update P(known), then a learning transition. Mastery is
> persisted per concept with a time-series, and a **spaced-review** `due_at` grows as mastery rises. The
> review queue surfaces weak/overdue concepts, which is what drives adaptive next-question selection. BKT is
> pure Python and fully unit-tested — given the same evidence it produces the same numbers."

**Likely probe — "why BKT over just averaging scores?"** Averaging ignores slip/guess noise and learning
over time; BKT gives a principled probability that updates correctly even from a single noisy attempt, and
it's interpretable (you can show the 0..1 mastery).

## 11.7 Deep dive #3 — Multi-agent orchestration
> "Two patterns. The chat is a **LangGraph supervisor** — best when one request must be classified and
> routed with state threaded through. The roadmap/study-plan is a **role crew** — Planner → Curator →
> Reviewer — a fixed pipeline where each role refines the previous output. I implemented the crew on my own
> LLM layer because CrewAI pulls ChromaDB/hnswlib, which needs a C++ toolchain that wasn't available — a
> good example of choosing a portable implementation over a heavy dependency."

## 11.8 The engineering problems I actually hit (and fixed)
These are the "tell me about a hard bug" stories — all real:
- **ChromaDB / PyTorch wouldn't install** (needs MSVC; torch is ~2 GB). → Switched to **fastembed (ONNX)** +
  a NumPy/pgvector store. Same embeddings, free, no compiler. *Lesson: pick dependencies that match the
  deployment reality.*
- **Cosine threshold didn't transfer** between dense (real) and sparse (mock) embeddings → fixed by using a
  low backstop threshold and enforcing grounding in the **prompt** + a judge, not a brittle absolute number.
- **SQLite returns naive datetimes** for tz-aware columns → the review-queue comparison threw a TypeError;
  fixed by coercing to UTC at the boundary.
- **WebSocket streaming + React Strict Mode** double-appended tokens → fixed with a **pure** state updater.
- **Provider auth quirks** (Gemini's `limit:0` free tier, OpenRouter base-URL/key mismatches) → motivated the
  **pluggable, env-driven model layer** so providers are interchangeable.

## 11.9 Trade-offs I made on purpose
- **NumPy store first, pgvector behind an interface** — ship something that runs everywhere, scale when needed.
- **Rule-based routing** instead of an LLM router — deterministic, free, testable; can upgrade later.
- **Mock-everything fallback** — no key → deterministic mock LLM, `EMBEDDINGS_MOCK=1` → hash vectors. This is
  why **CI runs the full suite with no API keys and no model downloads**.
- **Heavy optionals are lazy + gated** (faster-whisper, BLIP/torch) so the base app stays light.

## 11.10 How I'd scale / what's next
- Vector DB at scale (pgvector HNSW index / Qdrant), retrieval eval metrics (RAGAS faithfulness, precision@k).
- Prompt-injection **guardrails** on retrieved/web content, output validation.
- Caching + cost/latency dashboards; structured logging + Prometheus metrics.
- Background jobs (queue) for ingestion/transcription instead of inline.

## 11.11 Rapid-fire answers to expected questions
- **"How is it not just a GPT wrapper?"** Grounded cited RAG + a refusal path, BKT mastery modeling, an eval
  harness that scores factuality, and a provider-agnostic model layer — the wrapper is the smallest part.
- **"How do you test non-deterministic AI?"** Deterministic mocks for the LLM and embeddings, so behavior
  (routing, retrieval, citation shape, BKT math, the not-found path) is asserted without calling a model.
- **"What's the cost?"** Chat/roadmap run on a near-free model (deepseek) or fully free local (Ollama/Groq
  Llama); embeddings/transcription are local. A roadmap is ~$0.001; grounded answers are fractions of a cent.
- **"Where does it break?"** YouTube blocks datacenter IPs (mitigated with file upload + pasted text), and
  free-tier LLM rate limits — both handled with graceful fallbacks.
- **"What are you most proud of?"** That it's honestly *engineered* — grounding with a refusal path, a real
  knowledge-tracing model, an eval/observability story, and it runs end-to-end on free, open-source models.

## 11.12 Where each part lives in the app (point to it while you explain)

Sidebar labels → routes, so while you talk you can open the exact screen. "Demo cue" = what to
click to show it.

| Talking point (from §11) | UI page (sidebar) | URL | Backend endpoint(s) | Key code | Demo cue |
|---|---|---|---|---|---|
| **Chat tutor / LangGraph supervisor / streaming** | Chat Tutor | `/chat` | WS `…/api/chat/ws` | `agents/supervisor.py`, `app/(app)/chat/page.tsx` | Send a message → watch it stream token-by-token |
| **Grounded RAG + citations + refusal** ⭐ | My Materials | `/materials` | `POST /api/materials/ingest`, `/ingest/text`, `/ingest/url`, `/ask` | `agents/grounded.py`, `materials/store.py`, `app/(app)/materials/page.tsx` | Upload a PDF → ask a covered question (cited) → ask an unrelated one ("not in your materials") |
| **Embeddings (bge-small) + vector store / pgvector** | (powers My Materials) | `/materials` | same as above | `rag/embeddings.py`, `materials/store.py` | Explain it on the Materials page; show `VECTOR_BACKEND` swap |
| **Knowledge tracing (BKT) — visualization** ⭐ | Insights & Eval | `/insights` | `GET /api/learning/mastery`, `/review-queue` | `learning/bkt.py`, `learning/service.py`, `app/(app)/insights/page.tsx` | Show the **Concept mastery** bars + **Review queue** |
| **Knowledge tracing — where it's recorded** | Learn / Courses | `/arcade`, `/courses` | `POST /api/learning/attempt`, course quiz grade | `api/routes/courses.py`, `app/(app)/arcade/page.tsx` | Answer a quiz question → then show mastery move on Insights |
| **Learn: summarize / explain (interest) / quiz** | Learn | `/arcade` | `POST /api/game/summarize`, `/explain`, `/flashcards`, `/boss` | `agents/game_master.py`, `app/(app)/arcade/page.tsx` | Pick a topic → Summarize → Explain → Quiz me (green/red) |
| **Multi-agent role crew (Planner→Curator→Reviewer)** | Roadmap | `/plan` | `POST /api/plan`, `/plan/pdf`, `GET /plan/list` | `crew/roadmap.py`, `pdf.py`, `app/(app)/plan/page.tsx` | Build a roadmap → show phases + YouTube links → Download PDF |
| **YouTube playlist → trackable course** | Courses | `/courses` | `POST /api/courses`, per-step summarize/ask/quiz | `agents/course_agent.py`, `app/(app)/courses/page.tsx` | Open the demo course → complete a step → quiz |
| **Multimodal: image solver (vision)** | Study Tools | `/study` | `POST /api/study/solve-image` | `agents/vision.py`, `app/(app)/study/page.tsx` | Upload a photo of a problem → worked solution |
| **BM25 RAG (the other retrieval store)** | Study Tools | `/study` | `POST /api/study/documents`, `/ask` | `rag/store.py`, `agents/rag_agent.py` | Paste notes → ask a cited question |
| **Video RAG (whisper / transcript)** | Video RAG | `/video` | `POST /api/video/from-youtube`, `/upload`, `/{id}/ask` | `transcribe.py`, `app/(app)/video/page.tsx` | Upload a short clip → ask with `[mm:ss]` citation |
| **Sandboxed code run + Code-Review agent** | Code Playground | `/code` | `POST /api/code/run`, course `code-review` | `sandbox.py`, `agents/code_review.py`, `app/(app)/code/page.tsx` | Run code → get review verdict |
| **Eval harness: factuality / quiz-validity (LLM-as-judge)** | Insights & Eval | `/insights` | `POST /api/eval/factuality`, `/quiz-validity`, `GET /eval/results` | `eval/harness.py`, `api/routes/evaluation.py` | Show **Recent evaluations** (grounded vs hallucinated scores) |
| **Tracing (LangSmith status + in-app trace viewer / Langfuse)** | Insights & Eval | `/insights` | `GET /api/eval/obs-status`, `/traces` | `observability.py` | Show the tracing badge + **Recent traces** table |
| **Gamification (XP / streaks / badges / leaderboard)** | Learn + My Progress | `/arcade`, `/progress` | `GET /api/game/profile`, `/leaderboard` | `gamification/service.py` | Show the slim XP strip + leaderboard |
| **Analytics dashboards** | My Progress | `/progress` | `GET /api/analytics/me` | `api/routes/analytics.py`, `app/(app)/progress/page.tsx` | Show mastery/XP/weak-spot charts |
| **Pluggable LLM layer (OpenRouter/Groq/Ollama)** | (backend infra — no page) | — | every LLM call | `agents/llm.py`, `config.py` | Explain via env vars; mention `LLM_BACKEND` |
| **Auth (JWT access + rotating refresh)** | Login / Signup | `/login`, `/signup` | `POST /api/auth/*` | `core/security.py`, `api/routes/auth.py` | Mention token auto-refresh on 401 |

**Suggested live-demo order (≈3 min):** `/materials` (grounded cited answer + refusal) → answer a quiz in
`/arcade` → `/insights` (mastery bars move + factuality eval + traces) → `/plan` (multi-agent roadmap + PDF).
That sequence shows the three differentiators (grounding, knowledge tracing, multi-agent + eval) in order.
