"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

interface Resource { label: string; url: string; }
interface Phase {
  title: string;
  duration: string;
  topics: string[];
  resources: Resource[];
}
interface Roadmap {
  goal: string;
  hours_per_week: number;
  timeline: string;
  language: string;
  personalized_for: string[];
  phases: Phase[];
  review_notes: string;
  engine: string;
}

const tok = () => localStorage.getItem("sq_access") ?? undefined;

export default function RoadmapPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [hours, setHours] = useState(5);
  const [timeline, setTimeline] = useState("8 weeks");
  const [language, setLanguage] = useState("");
  const [plan, setPlan] = useState<Roadmap | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  async function generate() {
    if (!goal.trim()) return;
    setBusy(true);
    setPlan(null);
    try {
      setPlan(await apiFetch<Roadmap>("/plan", {
        method: "POST",
        body: JSON.stringify({ goal, hours_per_week: hours, timeline, language }),
      }, tok()));
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
    a.download = `roadmap-${plan.goal}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">🗺️ Roadmap</h1>
      <p className="mt-2 text-sm text-quest-muted">
        Tell me what you want to get proficient in and how much time you have. A Planner →
        Curator → Reviewer crew builds a time-boxed path — what to cover, in order, with YouTube
        lectures and resources — that you can download as a PDF.
      </p>

      <div className="mt-6 space-y-3 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
        <label className="block text-sm">
          <span className="text-quest-muted">I want to become proficient in…</span>
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Python, Agentic AI, Machine Learning, Organic Chemistry"
            className="mt-1 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-sm outline-none focus:border-quest-cyan"
          />
        </label>

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-sm">
            <span className="text-quest-muted">Hours / week</span>
            <input
              type="number" min={1} max={60} value={hours}
              onChange={(e) => setHours(Math.max(1, Number(e.target.value) || 1))}
              className="mt-1 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
            />
          </label>
          <label className="block text-sm">
            <span className="text-quest-muted">Target timeline</span>
            <select
              value={timeline}
              onChange={(e) => setTimeline(e.target.value)}
              className="mt-1 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
            >
              <option>2 weeks</option>
              <option>4 weeks</option>
              <option>8 weeks</option>
              <option>3 months</option>
              <option>6 months</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-quest-muted">Language (optional)</span>
            <input
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="e.g. Python, English, Hindi"
              className="mt-1 w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
            />
          </label>
        </div>

        <button onClick={generate} disabled={busy || !goal.trim()}
          className="rounded-xl bg-quest-violet px-6 py-3 text-sm font-display disabled:opacity-50">
          {busy ? "Crew building your roadmap…" : "Build my roadmap"}
        </button>
      </div>

      {plan && (
        <div className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold">{plan.goal}</h2>
            <button onClick={downloadPdf}
              className="rounded-lg border border-quest-muted/40 px-4 py-1.5 text-sm hover:border-quest-cyan">
              ⬇ Download PDF
            </button>
          </div>
          <p className="mt-1 text-xs text-quest-muted">
            {plan.timeline} · ~{plan.hours_per_week} hrs/week
            {plan.language && ` · ${plan.language}`}
            {plan.personalized_for.length > 0 && ` · focus: ${plan.personalized_for.join(", ")}`}
          </p>

          <ol className="mt-4 space-y-3">
            {plan.phases.map((p, i) => (
              <li key={i} className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="font-display font-semibold text-quest-cyan">{i + 1}. {p.title}</h3>
                  {p.duration && <span className="shrink-0 text-xs text-quest-muted">{p.duration}</span>}
                </div>
                <ul className="mt-2 list-disc pl-5 text-sm text-quest-muted">
                  {p.topics.map((t, j) => <li key={j}>{t}</li>)}
                </ul>
                {p.resources.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-quest-lime">Watch / read</p>
                    <ul className="mt-1 space-y-1 text-sm">
                      {p.resources.map((r, j) => (
                        <li key={j}>
                          <a href={r.url} target="_blank" rel="noreferrer" className="text-quest-cyan hover:underline">
                            {r.label}
                          </a>
                        </li>
                      ))}
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
