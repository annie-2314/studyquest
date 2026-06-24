"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

interface Video {
  id: string;
  title: string;
  chunks: number;
}
interface Citation {
  ref: string;
  content: string;
}

export default function VideoPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [videos, setVideos] = useState<Video[]>([]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState<Video | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  function token() {
    return localStorage.getItem("sq_access") ?? undefined;
  }
  const refresh = () => apiFetch<Video[]>("/video", {}, token()).then(setVideos).catch(() => {});
  useEffect(() => {
    if (user) refresh();
  }, [user]);

  async function ingest() {
    setError("");
    setBusy(true);
    try {
      const v = await apiFetch<Video>("/video/from-youtube", { method: "POST", body: JSON.stringify({ url }) }, token());
      setUrl("");
      setActive(v);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to ingest video");
    } finally {
      setBusy(false);
    }
  }

  async function uploadLocal(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch(`${BASE}/video/upload`, {
        method: "POST",
        headers: token() ? { Authorization: `Bearer ${token()}` } : {},
        body: fd,
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.detail ?? "Upload failed");
      } else {
        setActive(data);
        refresh();
      }
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  async function ask() {
    if (!active) return;
    setAnswer("");
    setCitations([]);
    try {
      const r = await apiFetch<{ answer: string; citations: Citation[] }>(
        `/video/${active.id}/ask`,
        { method: "POST", body: JSON.stringify({ question }) },
        token()
      );
      setAnswer(r.answer);
      setCitations(r.citations);
    } catch {
      setAnswer("Could not reach the server.");
    }
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Video RAG</h1>
      <p className="mt-2 text-sm text-quest-muted">
        Add a YouTube video by URL (file upload also supported when faster-whisper is installed),
        then ask questions answered with timestamp citations.
      </p>

      <div className="mt-6 flex gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
          className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-sm outline-none focus:border-quest-cyan"
        />
        <button onClick={ingest} disabled={busy || !url.trim()} className="rounded-xl bg-quest-violet px-6 py-3 text-sm font-display disabled:opacity-50">
          {busy ? "Transcribing…" : "Add video"}
        </button>
      </div>

      <div className="mt-3 flex items-center gap-3 text-sm text-quest-muted">
        <span>or upload a local video/audio file:</span>
        <label className="cursor-pointer rounded-lg border border-quest-muted/30 px-3 py-1.5 hover:border-quest-cyan">
          Choose file
          <input type="file" accept="video/*,audio/*" onChange={uploadLocal} className="hidden" />
        </label>
      </div>
      <p className="mt-1 text-xs text-quest-muted/70">
        Local transcription needs <code>faster-whisper</code> on the server; otherwise you&apos;ll get a
        message to install it (the YouTube-URL path always works).
      </p>
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}

      <div className="mt-6 flex flex-wrap gap-2">
        {videos.map((v) => (
          <button
            key={v.id}
            onClick={() => { setActive(v); setAnswer(""); setCitations([]); }}
            className={`rounded-lg border px-3 py-1.5 text-sm ${
              active?.id === v.id ? "border-quest-cyan text-quest-cyan" : "border-quest-muted/30 text-quest-muted"
            }`}
          >
            {v.title} ({v.chunks})
          </button>
        ))}
      </div>

      {active && (
        <div className="mt-6 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
          <p className="text-sm text-quest-muted">Asking about: <span className="text-quest-text">{active.title}</span></p>
          <div className="mt-3 flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask()}
              placeholder="e.g. explain what happens around minute 5"
              className="flex-1 rounded-lg border border-quest-muted/30 bg-quest-bg px-3 py-2 text-sm outline-none focus:border-quest-cyan"
            />
            <button onClick={ask} disabled={!question.trim()} className="rounded-lg bg-quest-violet px-4 py-2 text-sm disabled:opacity-50">
              Ask
            </button>
          </div>
          {answer && (
            <div className="mt-4">
              <pre className="whitespace-pre-wrap rounded-xl bg-quest-bg p-3 text-sm">{answer}</pre>
              {citations.length > 0 && (
                <div className="mt-3 space-y-1 text-xs text-quest-muted">
                  <p className="font-semibold text-quest-cyan">Timestamps</p>
                  {citations.map((c, i) => (
                    <p key={i}><span className="text-quest-lime">[{c.ref}]</span> {c.content}…</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
