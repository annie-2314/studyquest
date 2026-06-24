"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface RunResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
  timed_out: boolean;
}

export default function CodePage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState("print('Hello, StudyQuest!')\n");
  const [task, setTask] = useState("");
  const [run, setRun] = useState<RunResult | null>(null);
  const [review, setReview] = useState("");
  const [approved, setApproved] = useState<boolean | null>(null);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  function token() {
    return localStorage.getItem("sq_access") ?? undefined;
  }

  async function doRun() {
    setBusy("run");
    setReview("");
    setApproved(null);
    try {
      setRun(await apiFetch<RunResult>("/code/run", { method: "POST", body: JSON.stringify({ language, code }) }, token()));
    } catch {
      setRun({ ok: false, stdout: "", stderr: "Server error", exit_code: -1, timed_out: false });
    } finally {
      setBusy("");
    }
  }

  async function doReview() {
    setBusy("review");
    try {
      const r = await apiFetch<{ run: RunResult; review: string; approved: boolean }>(
        "/code/review",
        { method: "POST", body: JSON.stringify({ language, code, task }) },
        token()
      );
      setRun(r.run);
      setReview(r.review);
      setApproved(r.approved);
    } catch {
      setReview("Server error during review.");
    } finally {
      setBusy("");
    }
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Code Playground</h1>
      <p className="mt-2 text-sm text-quest-muted">
        Write code, run it in the sandbox, and get an AI code review. (Sandbox is timeout-bounded;
        for production use a Docker/Judge0 runner.)
      </p>

      <div className="mt-6 flex items-center gap-3">
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded-lg border border-quest-muted/30 bg-quest-bg px-3 py-2 text-sm"
        >
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
        </select>
        <input
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Task (optional, helps the reviewer)"
          className="flex-1 rounded-lg border border-quest-muted/30 bg-quest-bg px-3 py-2 text-sm outline-none focus:border-quest-cyan"
        />
      </div>

      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        spellCheck={false}
        rows={12}
        className="mt-3 w-full rounded-xl border border-quest-muted/30 bg-[#0a0818] p-4 font-mono text-sm text-quest-text outline-none focus:border-quest-cyan"
      />

      <div className="mt-3 flex gap-2">
        <button onClick={doRun} disabled={!!busy} className="rounded-xl bg-quest-violet px-5 py-2 text-sm font-display disabled:opacity-50">
          {busy === "run" ? "Running…" : "▶ Run"}
        </button>
        <button onClick={doReview} disabled={!!busy} className="rounded-xl border border-quest-muted/40 px-5 py-2 text-sm font-display hover:border-quest-cyan disabled:opacity-50">
          {busy === "review" ? "Reviewing…" : "🔍 Review"}
        </button>
      </div>

      {run && (
        <div className="mt-4">
          <p className="text-xs text-quest-muted">
            exit {run.exit_code}
            {run.timed_out && " · timed out"}
            {run.ok ? " · ✓ ok" : " · ✗ error"}
          </p>
          {run.stdout && <pre className="mt-1 whitespace-pre-wrap rounded-xl bg-quest-bg p-3 text-sm">{run.stdout}</pre>}
          {run.stderr && <pre className="mt-1 whitespace-pre-wrap rounded-xl bg-quest-bg p-3 text-sm text-red-400">{run.stderr}</pre>}
        </div>
      )}

      {review && (
        <div className="mt-4 rounded-xl border border-quest-muted/20 bg-quest-surface p-4">
          <p className={`text-sm font-display ${approved ? "text-quest-lime" : "text-quest-cyan"}`}>
            {approved ? "✓ Passed review" : "Needs work"}
          </p>
          <pre className="mt-2 whitespace-pre-wrap text-sm">{review}</pre>
        </div>
      )}
    </main>
  );
}
