"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const tok = () => localStorage.getItem("sq_access") ?? undefined;

interface TraceRun {
  name: string;
  run_type: string;
  status: string;
  latency_ms: number | null;
  tokens: number | null;
  start_time: string | null;
}
interface TracesResp {
  enabled: boolean;
  runs: TraceRun[];
  error?: string;
}
interface ConceptMastery { concept: string; p_known: number; attempts: number; correct: number; due_at: string | null; }
interface MasteryResp { concepts: ConceptMastery[]; history: { concept: string; p_known: number; at: string | null }[]; }
interface ReviewItem { concept: string; p_known: number; due: boolean; }
interface EvalRow { kind: string; score: number; passed: boolean; detail: string; at: string | null; }

export default function InsightsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [obs, setObs] = useState<{ tracing: boolean; project: string | null } | null>(null);
  const [quiz, setQuiz] = useState<{ enough_data: boolean; first_half: number | null; second_half: number | null; improved: boolean | null } | null>(null);
  const [answer, setAnswer] = useState("A variable stores a value. For example, age = 5.");
  const [verdict, setVerdict] = useState<{ score: number; rationale: string } | null>(null);
  const [traces, setTraces] = useState<TracesResp | null>(null);
  const [tracesBusy, setTracesBusy] = useState(false);
  const [mastery, setMastery] = useState<MasteryResp | null>(null);
  const [review, setReview] = useState<ReviewItem[]>([]);
  const [evals, setEvals] = useState<EvalRow[]>([]);

  const loadTraces = () => {
    setTracesBusy(true);
    apiFetch<TracesResp>("/eval/traces", {}, tok())
      .then(setTraces).catch(() => {}).finally(() => setTracesBusy(false));
  };

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);
  useEffect(() => {
    if (user) {
      apiFetch<{ tracing: boolean; project: string | null }>("/eval/obs-status", {}, tok()).then(setObs).catch(() => {});
      apiFetch<typeof quiz>("/eval/quiz-improvement", {}, tok()).then(setQuiz).catch(() => {});
      apiFetch<MasteryResp>("/learning/mastery", {}, tok()).then(setMastery).catch(() => {});
      apiFetch<ReviewItem[]>("/learning/review-queue", {}, tok()).then(setReview).catch(() => {});
      apiFetch<EvalRow[]>("/eval/results", {}, tok()).then(setEvals).catch(() => {});
      loadTraces();
    }
  }, [user]);

  async function judge() {
    setVerdict(await apiFetch("/eval/explanation", { method: "POST", body: JSON.stringify({ question: "Explain variables", answer }) }, tok()));
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Insights & Eval</h1>

      {/* Knowledge tracing: per-concept mastery (BKT) */}
      <section className="mt-6 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <h2 className="font-display font-semibold text-quest-cyan">Concept mastery</h2>
        {!mastery || mastery.concepts.length === 0 ? (
          <p className="mt-2 text-sm text-quest-muted">
            No mastery data yet — answer some quiz questions (Learn or Courses) and your per-concept
            mastery will appear here.
          </p>
        ) : (
          <div className="mt-3 space-y-2">
            {mastery.concepts.map((c) => {
              const pct = Math.round(c.p_known * 100);
              const color = pct >= 80 ? "bg-quest-lime" : pct >= 50 ? "bg-quest-cyan" : "bg-red-400";
              return (
                <div key={c.concept}>
                  <div className="flex justify-between text-xs">
                    <span className="text-quest-text">{c.concept}</span>
                    <span className="text-quest-muted">{pct}% · {c.correct}/{c.attempts}</span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-quest-bg">
                    <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {review.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-quest-cyan">Review queue</p>
            <div className="mt-1 flex flex-wrap gap-2">
              {review.map((r) => (
                <span key={r.concept}
                  className={`rounded-full px-3 py-1 text-xs ${r.due ? "bg-red-400/20 text-red-300" : "bg-quest-bg text-quest-muted"}`}>
                  {r.due ? "⏰ " : ""}{r.concept} · {Math.round(r.p_known * 100)}%
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="mt-4 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-quest-cyan">LangSmith tracing</h2>
          <span className={`rounded-full px-3 py-0.5 text-xs ${obs?.tracing ? "bg-quest-lime/20 text-quest-lime" : "bg-quest-bg text-quest-muted"}`}>
            {obs?.tracing ? "● On" : "○ Off"}
          </span>
        </div>
        <p className="mt-2 text-sm text-quest-muted">
          {obs?.tracing
            ? `Live. Every agent step (prompt, response, latency, tokens) is traced to the "${obs.project}" project in LangSmith.`
            : "Optional observability. Set LANGCHAIN_API_KEY + LANGCHAIN_TRACING_V2 in the backend env to trace every LLM/agent step to LangSmith."}
        </p>

        {obs?.tracing && (
          <div className="mt-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-quest-text">Recent traces</h3>
              <div className="flex items-center gap-3 text-xs">
                <button onClick={loadTraces} className="text-quest-cyan hover:underline">
                  {tracesBusy ? "Refreshing…" : "↻ Refresh"}
                </button>
                <a href="https://smith.langchain.com" target="_blank" rel="noreferrer" className="text-quest-cyan hover:underline">
                  Open in LangSmith ↗
                </a>
              </div>
            </div>

            {traces?.error && <p className="mt-2 text-xs text-red-400">{traces.error}</p>}
            {traces && !traces.error && traces.runs.length === 0 && (
              <p className="mt-2 text-xs text-quest-muted">
                No traces yet — use the Chat Tutor or build a Roadmap, then hit Refresh.
              </p>
            )}

            {traces && traces.runs.length > 0 && (
              <div className="mt-2 overflow-hidden rounded-xl border border-quest-muted/20">
                <table className="w-full text-left text-xs">
                  <thead className="bg-quest-bg text-quest-muted">
                    <tr>
                      <th className="px-3 py-2 font-medium">Step</th>
                      <th className="px-3 py-2 font-medium">Status</th>
                      <th className="px-3 py-2 font-medium">Latency</th>
                      <th className="px-3 py-2 font-medium">Tokens</th>
                      <th className="px-3 py-2 font-medium">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {traces.runs.map((r, i) => (
                      <tr key={i} className="border-t border-quest-muted/10">
                        <td className="px-3 py-2">{r.name}</td>
                        <td className={`px-3 py-2 ${r.status === "error" ? "text-red-400" : "text-quest-lime"}`}>
                          {r.status === "error" ? "✗ error" : "✓ ok"}
                        </td>
                        <td className="px-3 py-2 text-quest-muted">{r.latency_ms != null ? `${r.latency_ms} ms` : "—"}</td>
                        <td className="px-3 py-2 text-quest-muted">{r.tokens ?? "—"}</td>
                        <td className="px-3 py-2 text-quest-muted">
                          {r.start_time ? new Date(r.start_time).toLocaleTimeString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="mt-4 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <h2 className="font-display font-semibold text-quest-cyan">Quiz improvement</h2>
        {quiz?.enough_data ? (
          <p className="mt-2 text-sm text-quest-muted">
            Pass-rate: {Math.round((quiz.first_half ?? 0) * 100)}% → {Math.round((quiz.second_half ?? 0) * 100)}%{" "}
            {quiz.improved ? "📈 improving" : "—"}
          </p>
        ) : (
          <p className="mt-2 text-sm text-quest-muted">Not enough quiz data yet — complete more course steps.</p>
        )}
      </section>

      <section className="mt-4 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <h2 className="font-display font-semibold text-quest-cyan">LLM-as-judge: explanation quality</h2>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          rows={3}
          className="mt-2 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-3 py-2 text-sm outline-none focus:border-quest-cyan"
        />
        <button onClick={judge} className="mt-2 rounded-xl bg-quest-violet px-4 py-2 text-sm font-display">Score it</button>
        {verdict && (
          <p className="mt-3 text-sm">
            <span className="font-display text-quest-lime">{verdict.score}/5</span> — {verdict.rationale}
          </p>
        )}
      </section>

      {/* Persisted factuality / quiz-validity evals */}
      <section className="mt-4 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <h2 className="font-display font-semibold text-quest-cyan">Recent evaluations</h2>
        {evals.length === 0 ? (
          <p className="mt-2 text-sm text-quest-muted">
            No eval runs yet — grounded answers and quizzes get factuality/validity-scored here
            (grounded vs hallucinated).
          </p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm">
            {evals.map((e, i) => (
              <li key={i} className="flex items-center justify-between gap-3 rounded-lg bg-quest-bg px-3 py-2">
                <span className="text-quest-muted">
                  <span className={e.passed ? "text-quest-lime" : "text-red-400"}>
                    {e.passed ? "✓" : "✗"}
                  </span>{" "}
                  <span className="text-quest-text">{e.kind}</span> · {Math.round(e.score * 100)}%
                  {e.detail && <span className="ml-1 text-quest-muted/70">— {e.detail}</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
