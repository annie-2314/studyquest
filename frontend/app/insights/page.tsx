"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const tok = () => localStorage.getItem("sq_access") ?? undefined;

export default function InsightsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [obs, setObs] = useState<{ tracing: boolean; project: string | null } | null>(null);
  const [quiz, setQuiz] = useState<{ enough_data: boolean; first_half: number | null; second_half: number | null; improved: boolean | null } | null>(null);
  const [answer, setAnswer] = useState("A variable stores a value. For example, age = 5.");
  const [verdict, setVerdict] = useState<{ score: number; rationale: string } | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);
  useEffect(() => {
    if (user) {
      apiFetch<{ tracing: boolean; project: string | null }>("/eval/obs-status", {}, tok()).then(setObs).catch(() => {});
      apiFetch<typeof quiz>("/eval/quiz-improvement", {}, tok()).then(setQuiz).catch(() => {});
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

      <section className="mt-6 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <h2 className="font-display font-semibold text-quest-cyan">LangSmith tracing</h2>
        <p className="mt-2 text-sm text-quest-muted">
          {obs?.tracing
            ? `On — project "${obs.project}". Every agent step is traced.`
            : "Off — set LANGCHAIN_API_KEY + LANGCHAIN_TRACING_V2 in backend/.env to trace every agent step."}
        </p>
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
    </main>
  );
}
