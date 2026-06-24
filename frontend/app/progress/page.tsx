"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface Analytics {
  xp: number;
  level: number;
  streak: number;
  longest_streak: number;
  badges_earned: number;
  courses: { title: string; percent: number }[];
  completed_steps: number;
  quizzes_passed: number;
  messages: number;
  weak_spots: string[];
  strengths: string[];
}

const tok = () => localStorage.getItem("sq_access") ?? undefined;

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-4 text-center">
      <p className="font-display text-2xl font-bold text-quest-lime">{value}</p>
      <p className="mt-1 text-xs text-quest-muted">{label}</p>
    </div>
  );
}

export default function ProgressPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [a, setA] = useState<Analytics | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);
  useEffect(() => {
    if (user) apiFetch<Analytics>("/analytics/me", {}, tok()).then(setA).catch(() => {});
  }, [user]);

  if (loading || !user || !a) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Your Progress</h1>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Level" value={a.level} />
        <Stat label="XP" value={a.xp} />
        <Stat label="Streak" value={`${a.streak}🔥`} />
        <Stat label="Badges" value={a.badges_earned} />
        <Stat label="Steps done" value={a.completed_steps} />
        <Stat label="Quizzes passed" value={a.quizzes_passed} />
        <Stat label="Tutor messages" value={a.messages} />
        <Stat label="Longest streak" value={a.longest_streak} />
      </div>

      {a.courses.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display text-lg font-semibold">Course completion</h2>
          <div className="mt-3 h-64 rounded-2xl border border-quest-muted/20 bg-quest-surface p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={a.courses}>
                <XAxis dataKey="title" tick={{ fill: "#A89FC9", fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "#A89FC9", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#171231", border: "none", borderRadius: 12 }} />
                <Bar dataKey="percent" radius={[6, 6, 0, 0]}>
                  {a.courses.map((_, i) => <Cell key={i} fill="#A3E635" />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
          <h3 className="font-display font-semibold text-quest-cyan">Weak spots</h3>
          {a.weak_spots.length ? (
            <ul className="mt-2 list-disc pl-5 text-sm text-quest-muted">
              {a.weak_spots.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          ) : <p className="mt-2 text-sm text-quest-muted">None tracked yet — keep learning!</p>}
        </div>
        <div className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-5">
          <h3 className="font-display font-semibold text-quest-cyan">Strengths</h3>
          {a.strengths.length ? (
            <ul className="mt-2 list-disc pl-5 text-sm text-quest-muted">
              {a.strengths.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          ) : <p className="mt-2 text-sm text-quest-muted">Building these up as you go.</p>}
        </div>
      </section>
    </main>
  );
}
