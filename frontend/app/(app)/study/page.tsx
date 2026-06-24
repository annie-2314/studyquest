"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

interface Citation {
  ref: string;
  content: string;
}

export default function StudyPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  // image solver
  const [imgAnswer, setImgAnswer] = useState("");
  const [imgBusy, setImgBusy] = useState(false);

  // knowledge base
  const [docTitle, setDocTitle] = useState("");
  const [docText, setDocText] = useState("");
  const [docMsg, setDocMsg] = useState("");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [askBusy, setAskBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  async function onImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImgBusy(true);
    setImgAnswer("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const token = localStorage.getItem("sq_access");
      const resp = await fetch(`${BASE}/study/solve-image`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      });
      const data = await resp.json();
      setImgAnswer(data.answer ?? data.detail ?? "Failed");
    } catch {
      setImgAnswer("Could not reach the server.");
    } finally {
      setImgBusy(false);
    }
  }

  async function addDoc() {
    setDocMsg("");
    try {
      const token = localStorage.getItem("sq_access") ?? undefined;
      const r = await apiFetch<{ chunks: number }>(
        "/study/documents",
        { method: "POST", body: JSON.stringify({ title: docTitle, text: docText }) },
        token
      );
      setDocMsg(`Saved — ${r.chunks} chunk(s) indexed.`);
      setDocTitle("");
      setDocText("");
    } catch {
      setDocMsg("Could not save document.");
    }
  }

  async function ask() {
    setAskBusy(true);
    setAnswer("");
    setCitations([]);
    try {
      const token = localStorage.getItem("sq_access") ?? undefined;
      const r = await apiFetch<{ answer: string; citations: Citation[] }>(
        "/study/ask",
        { method: "POST", body: JSON.stringify({ query }) },
        token
      );
      setAnswer(r.answer);
      setCitations(r.citations);
    } catch {
      setAnswer("Could not reach the server.");
    } finally {
      setAskBusy(false);
    }
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">
        ← Dashboard
      </Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Study Tools</h1>

      {/* Image solver */}
      <section className="mt-8 rounded-2xl border border-quest-muted/20 bg-quest-surface p-6">
        <h2 className="font-display text-lg font-semibold text-quest-cyan">📸 Solve from a photo</h2>
        <p className="mt-1 text-sm text-quest-muted">
          Upload a handwritten problem or textbook page — the vision tutor reads and explains it.
        </p>
        <input type="file" accept="image/*" onChange={onImage} className="mt-4 text-sm" />
        {imgBusy && <p className="mt-3 text-sm text-quest-muted">Reading the image…</p>}
        {imgAnswer && (
          <pre className="mt-4 whitespace-pre-wrap rounded-xl bg-quest-bg p-4 text-sm">{imgAnswer}</pre>
        )}
      </section>

      {/* Knowledge base */}
      <section className="mt-6 rounded-2xl border border-quest-muted/20 bg-quest-surface p-6">
        <h2 className="font-display text-lg font-semibold text-quest-cyan">📚 Knowledge base (RAG)</h2>
        <p className="mt-1 text-sm text-quest-muted">
          Paste notes, then ask grounded questions — answers cite the source passages.
        </p>
        <input
          value={docTitle}
          onChange={(e) => setDocTitle(e.target.value)}
          placeholder="Document title"
          className="mt-4 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
        />
        <textarea
          value={docText}
          onChange={(e) => setDocText(e.target.value)}
          placeholder="Paste your notes / material here…"
          rows={4}
          className="mt-2 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
        />
        <button
          onClick={addDoc}
          disabled={!docText.trim()}
          className="mt-2 rounded-xl bg-quest-violet px-4 py-2 text-sm font-display disabled:opacity-50"
        >
          Add to knowledge base
        </button>
        {docMsg && <p className="mt-2 text-sm text-quest-lime">{docMsg}</p>}

        <div className="mt-6 flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="Ask a question about your notes…"
            className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
          />
          <button
            onClick={ask}
            disabled={askBusy || !query.trim()}
            className="rounded-xl bg-quest-violet px-5 py-2 text-sm font-display disabled:opacity-50"
          >
            {askBusy ? "…" : "Ask"}
          </button>
        </div>
        {answer && (
          <div className="mt-4">
            <pre className="whitespace-pre-wrap rounded-xl bg-quest-bg p-4 text-sm">{answer}</pre>
            {citations.length > 0 && (
              <div className="mt-3 space-y-1 text-xs text-quest-muted">
                <p className="font-semibold text-quest-cyan">Sources</p>
                {citations.map((c, i) => (
                  <p key={i}>
                    <span className="text-quest-lime">[{c.ref}]</span> {c.content}…
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
