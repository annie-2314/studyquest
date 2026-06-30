"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import Markdown from "@/components/Markdown";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const tok = () => localStorage.getItem("sq_access") ?? undefined;

interface Material { id: string; title: string; kind: string; chunks: number; created_at: string; }
interface Citation { ref: string; page: number; snippet: string; }
interface Answer { answer: string; citations: Citation[]; grounded: boolean; }

function kindIcon(k: string) {
  return k === "pdf" ? "📕" : k === "url" ? "🌐" : k === "video" ? "🎬" : "📝";
}

export default function MaterialsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [materials, setMaterials] = useState<Material[]>([]);
  const [scope, setScope] = useState("");          // "" = all materials
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [ans, setAns] = useState<Answer | null>(null);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const refresh = () => apiFetch<Material[]>("/materials", {}, tok()).then(setMaterials).catch(() => {});
  useEffect(() => { if (user) refresh(); }, [user]);

  async function ingestText() {
    if (!text.trim()) return;
    setBusy(true); setError("");
    try {
      await apiFetch("/materials/ingest/text", {
        method: "POST", body: JSON.stringify({ title: title || "Pasted notes", text }),
      }, tok());
      setText(""); setTitle(""); refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to ingest");
    } finally { setBusy(false); }
  }

  async function ingestPdf(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("title", title || file.name);
      const resp = await fetch(`${BASE}/materials/ingest`, {
        method: "POST",
        headers: tok() ? { Authorization: `Bearer ${tok()}` } : {},
        body: fd,
      });
      const data = await resp.json();
      if (!resp.ok) setError(data.detail ?? "Upload failed");
      else { setTitle(""); refresh(); }
    } catch {
      setError("Could not reach the server.");
    } finally { setBusy(false); }
  }

  async function ingestUrl() {
    if (!url.trim()) return;
    setBusy(true); setError("");
    try {
      await apiFetch("/materials/ingest/url", {
        method: "POST", body: JSON.stringify({ url, title: title || "Video transcript" }),
      }, tok());
      setUrl(""); setTitle(""); refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to ingest URL");
    } finally { setBusy(false); }
  }

  async function ask() {
    if (!question.trim()) return;
    setAsking(true); setAns(null);
    try {
      const r = await apiFetch<Answer>("/materials/ask", {
        method: "POST",
        body: JSON.stringify({ question, material_id: scope || null }),
      }, tok());
      setAns(r);
    } catch (e) {
      setAns({ answer: `⚠️ ${e instanceof ApiError ? e.detail : "Failed"}`, citations: [], grounded: false });
    } finally { setAsking(false); }
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">📚 My Materials</h1>
      <p className="mt-2 text-sm text-quest-muted">
        Upload a PDF or paste notes. Answers come <span className="text-quest-text">only from your
        sources</span>, with citations — if it&apos;s not in your materials, the tutor says so instead
        of guessing.
      </p>

      {/* Ingest */}
      <section className="mt-6 space-y-3 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <input
          value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Title (optional)"
          className="w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
        />
        <textarea
          value={text} onChange={(e) => setText(e.target.value)} rows={4}
          placeholder="Paste notes / text here…"
          className="w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
        />
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={ingestText} disabled={busy || !text.trim()}
            className="rounded-xl bg-quest-violet px-5 py-2 text-sm font-display disabled:opacity-50">
            {busy ? "Indexing…" : "Add notes"}
          </button>
          <label className="cursor-pointer rounded-xl border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan">
            📕 Upload PDF
            <input type="file" accept="application/pdf" onChange={ingestPdf} className="hidden" />
          </label>
          {busy && <span className="text-xs text-quest-muted">working…</span>}
        </div>
        <div className="flex gap-2">
          <input
            value={url} onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ingestUrl()}
            placeholder="…or a YouTube URL (transcript → indexed)"
            className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
          />
          <button onClick={ingestUrl} disabled={busy || !url.trim()}
            className="rounded-xl border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan disabled:opacity-50">
            🎬 Add from URL
          </button>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <p className="text-xs text-quest-muted/70">Embedded locally with bge-small — free, no API key needed for indexing.</p>
      </section>

      {/* Library */}
      {materials.length > 0 && (
        <section className="mt-6">
          <h2 className="font-display text-sm font-semibold text-quest-muted">Your sources</h2>
          <div className="mt-2 flex flex-wrap gap-2">
            <button onClick={() => setScope("")}
              className={`rounded-lg border px-3 py-1.5 text-sm ${scope === "" ? "border-quest-cyan text-quest-cyan" : "border-quest-muted/30 text-quest-muted"}`}>
              All
            </button>
            {materials.map((m) => (
              <button key={m.id} onClick={() => setScope(m.id)}
                className={`rounded-lg border px-3 py-1.5 text-sm ${scope === m.id ? "border-quest-cyan text-quest-cyan" : "border-quest-muted/30 text-quest-muted"}`}>
                {kindIcon(m.kind)} {m.title} ({m.chunks})
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Grounded Q&A */}
      <section className="mt-6 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <div className="flex gap-2">
          <input
            value={question} onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="Ask a question about your materials…"
            className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
          />
          <button onClick={ask} disabled={asking || !question.trim()}
            className="rounded-xl bg-quest-violet px-5 py-2 text-sm disabled:opacity-50">
            {asking ? "…" : "Ask"}
          </button>
        </div>

        {ans && (
          <div className="mt-4">
            <div className={`rounded-xl p-3 text-sm ${ans.grounded ? "bg-quest-bg" : "bg-quest-bg/50 text-quest-muted"}`}>
              <Markdown>{ans.answer}</Markdown>
            </div>
            {ans.citations.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-quest-cyan">Citations</p>
                <ul className="mt-1 space-y-1 text-xs text-quest-muted">
                  {ans.citations.map((c, i) => (
                    <li key={i}>
                      <span className="text-quest-lime">[{c.ref}]</span> {c.snippet}…
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
