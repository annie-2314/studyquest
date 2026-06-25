# Deploying StudyQuest AI (free)

This app is two services that must be deployed separately:

- **Backend** — FastAPI + **WebSockets** (the chat tutor streams over a WS).
  WebSockets need a real, always-on server — **not** a serverless function.
- **Frontend** — Next.js (App Router).

> **Why this matters:** Vercel/Netlify can host the Next.js frontend, but they
> **cannot** host the WebSocket backend (no long-lived connections on their free
> serverless runtime). The backend needs a host that keeps a process running:
> Render, Railway, Fly.io, Koyeb, or Hugging Face Spaces.

---

## Recommended free setups

| Setup | Backend (WS) | Frontend | DB (persistent) | Notes |
|-------|--------------|----------|-----------------|-------|
| **A — all Render** (simplest) | Render Web Service | Render Web Service | Neon Postgres | One dashboard. Use the included `render.yaml`. |
| **B — split** (best frontend) | Render Web Service | **Vercel** | Neon Postgres | Vercel is the nicest Next.js host; backend stays on Render. |

Both are 100% free. Pick A if you want one place; pick B if you want the
snappiest frontend.

---

## Prerequisites

1. **Push to GitHub** (Render and Vercel deploy from a Git repo):
   ```bash
   cd "C:/Users/TEAMAPEX-003/Downloads/tutor"
   git init
   git add .
   git commit -m "StudyQuest AI"
   git branch -M main
   git remote add origin https://github.com/<you>/studyquest.git
   git push -u origin main
   ```
   `backend/.env` is git-ignored — your OpenRouter key is **not** pushed. You'll
   re-enter it as an environment variable on the host (kept secret there).

2. **A free Postgres (recommended).** Render's free disk is *ephemeral* — the
   SQLite file resets on every deploy/restart, so accounts disappear. For data
   that sticks, create a free Postgres at **[Neon](https://neon.tech)** or
   **[Supabase](https://supabase.com)** and copy its connection string
   (`postgresql://user:pass@host/db`). The app already supports it via
   `DATABASE_URL` (driver `psycopg2-binary` is in `requirements.txt`), and it
   auto-creates its tables on first boot.

---

## Setup A — everything on Render (with `render.yaml`)

1. Render → **New +** → **Blueprint** → select your repo. It reads `render.yaml`
   and creates **studyquest-api** and **studyquest-web**.
2. On **studyquest-api**, set the secret env vars:
   - `OPENROUTER_API_KEY` = your key
   - `DATABASE_URL` = your Neon/Supabase URL (optional but recommended)
3. First deploy finishes → note the two URLs, e.g.
   `https://studyquest-api.onrender.com` and `https://studyquest-web.onrender.com`.
4. **Wire them together** (this is the step everyone forgets):
   - **studyquest-web** → env `NEXT_PUBLIC_API_BASE` = `https://studyquest-api.onrender.com/api`
   - **studyquest-api** → env `FRONTEND_ORIGIN` = `https://studyquest-web.onrender.com`
5. Redeploy **both** (web must rebuild — `NEXT_PUBLIC_*` is baked in at build
   time; api must restart so CORS picks up `FRONTEND_ORIGIN`).
6. Open the web URL and sign up. 🎉

The WebSocket URL is derived automatically: the frontend turns the `https://…/api`
base into `wss://…/api/chat/ws`, so no extra config is needed.

---

## Setup B — backend on Render, frontend on Vercel

**Backend (Render):** same as A but only the `studyquest-api` service (you can
delete the web service from the blueprint, or create the service manually):

- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL_FAST=deepseek/deepseek-chat`,
  `OPENROUTER_MODEL_SMART=openai/gpt-4o-mini`, `SECRET_KEY` (any long random
  string), `DATABASE_URL` (Neon/Supabase), and `FRONTEND_ORIGIN` (your Vercel
  URL, set after the frontend is live).

**Frontend (Vercel):**
1. Vercel → **Add New** → **Project** → import the repo.
2. Set **Root Directory** = `frontend`.
3. Add env var `NEXT_PUBLIC_API_BASE` = `https://<your-api>.onrender.com/api`.
4. Deploy. Copy the Vercel URL and put it in the backend's `FRONTEND_ORIGIN`,
   then restart the backend.

---

## Known free-tier limitations (not bugs)

- **Cold starts:** Render free services sleep after ~15 min idle; the next
  request wakes them in ~30–60s. (A free uptime pinger like UptimeRobot can keep
  the API warm.)
- **YouTube features:** Courses (playlist → course) and Video-RAG *by URL* rely
  on `yt-dlp`/transcripts. YouTube aggressively blocks **datacenter IPs**, so
  these may fail in the cloud even though they work locally. Everything else
  (Chat, Learn, Roadmap, Study Tools, paste-a-URL, Code, quizzes, PDF) works.
- **SQLite is ephemeral** on free hosts — use Postgres (above) for persistence.
- **Free Postgres caps:** Neon/Supabase free tiers are generous for a demo but
  have storage/connection limits; fine for this app.

---

## Other free hosts that work for the backend

- **Railway** — very easy; free tier is a limited monthly credit.
- **Fly.io** — free allowance, WS-friendly, Docker-based (a bit more setup).
- **Koyeb** — free web service, supports WebSockets.
- **Hugging Face Spaces** — free Docker Space can run FastAPI; good for demos,
  though WS proxying and persistent storage are quirky.
