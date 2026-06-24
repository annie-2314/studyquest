"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Dashboard() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-display text-3xl font-bold">Welcome, {user.display_name} 👋</h1>
      <p className="mt-3 text-quest-muted">Pick up your quest where you left off.</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Link
          href="/chat"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">💬 Chat Tutor</h2>
          <p className="mt-2 text-sm text-quest-muted">
            Ask anything. The supervisor routes you to the right specialist agent and streams the answer live.
          </p>
        </Link>
        <Link
          href="/study"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">🧪 Study Tools</h2>
          <p className="mt-2 text-sm text-quest-muted">
            Solve a problem from a photo, or build a knowledge base and ask grounded, cited questions.
          </p>
        </Link>
        <Link
          href="/courses"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">🗺️ Course Roadmaps</h2>
          <p className="mt-2 text-sm text-quest-muted">
            Paste a YouTube playlist → a step-by-step quest with summaries, Q&amp;A, and quizzes.
          </p>
        </Link>
        <Link
          href="/code"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">💻 Code Playground</h2>
          <p className="mt-2 text-sm text-quest-muted">
            Write code, run it in a sandbox, and get an AI code review for coding courses.
          </p>
        </Link>
        <Link
          href="/video"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">🎬 Video RAG</h2>
          <p className="mt-2 text-sm text-quest-muted">
            Add a video, then ask questions answered with timestamp citations.
          </p>
        </Link>
        <Link
          href="/arcade"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">🎮 Arcade</h2>
          <p className="mt-2 text-sm text-quest-muted">
            XP, levels, streaks, badges, leaderboard, flashcards, and boss-battle quizzes.
          </p>
        </Link>
        <Link
          href="/plan"
          className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-6 hover:border-quest-cyan"
        >
          <h2 className="font-display text-lg font-semibold text-quest-cyan">📝 Study Plan + PDF</h2>
          <p className="mt-2 text-sm text-quest-muted">
            A multi-agent crew builds a personalized study plan you can download as a PDF.
          </p>
        </Link>
      </div>

      <button
        onClick={logout}
        className="mt-8 rounded-xl border border-quest-muted/40 px-5 py-2 hover:border-quest-cyan"
      >
        Log out
      </button>
    </main>
  );
}
