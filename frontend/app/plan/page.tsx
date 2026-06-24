"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

interface Module {
  title: string;
  objectives: string[];
  practice_questions?: string[];
}
interface Plan {
  topic: string;
  personalized_for: string[];
  modules: Module[];
  review_notes: string;
  engine: string;
}

const tok = () => localStorage.getItem("sq_access") ?? undefined;

export default function PlanPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  async function generate() {
    setBusy(true);
    setPlan(null);
    try {
      setPlan(await apiFetch<Plan>("/plan", { method: "POST", body: JSON.stringify({ topic }) }, tok()));
    } finally {
      setBusy(false);
    }
  }

  async function downloadPdf() {
    if (!plan) return;
    const resp = await fetch(`${BASE}/plan/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${tok()}` },
      body: JSON.stringify(plan),
    });
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `studyquest-${plan.topic}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Study Plan Crew</h1>
      <p className="mt-2 text-sm text-quest-muted">
        A Planner → Question-Writer → Reviewer crew builds a personalized plan (using your stored
        weak spots), exportable as a PDF.
      </p>

      <div className="mt-6 flex gap-2">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What do you want to learn?"
          className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-sm outline-none focus:border-quest-cyan"
        />
        <button onClick={generate} disabled={busy || !topic.trim()} className="rounded-xl bg-quest-violet px-6 py-3 text-sm font-display disabled:opacity-50">
          {busy ? "Crew working…" : "Build plan"}
        </button>
      </div>

      {plan && (
        <div className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold">{plan.topic}</h2>
            <button onClick={downloadPdf} className="rounded-lg border border-quest-muted/40 px-4 py-1.5 text-sm hover:border-quest-cyan">
              ⬇ Download PDF
            </button>
          </div>
          <p className="mt-1 text-xs text-quest-muted">engine: {plan.engine}
            {plan.personalized_for.length > 0 && ` · focus: ${plan.personalized_for.join(", ")}`}</p>

          <ol className="mt-4 space-y-3">
            {plan.modules.map((m, i) => (
              <li key={i} className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
                <h3 className="font-display font-semibold text-quest-cyan">{i + 1}. {m.title}</h3>
                <ul className="mt-2 list-disc pl-5 text-sm text-quest-muted">
                  {m.objectives.map((o, j) => <li key={j}>{o}</li>)}
                </ul>
                {m.practice_questions && m.practice_questions.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-quest-lime">Practice</p>
                    <ul className="mt-1 list-decimal pl-5 text-sm">
                      {m.practice_questions.map((q, j) => <li key={j}>{q}</li>)}
                    </ul>
                  </div>
                )}
              </li>
            ))}
          </ol>
          {plan.review_notes && (
            <p className="mt-4 rounded-xl bg-quest-surface p-4 text-sm text-quest-muted">
              <span className="text-quest-cyan">Reviewer:</span> {plan.review_notes}
            </p>
          )}
        </div>
      )}
    </main>
  );
}
