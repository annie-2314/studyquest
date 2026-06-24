"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

const QUICK = [
  { href: "/chat", icon: "💬", title: "Chat Tutor", desc: "Ask anything — the supervisor routes you to the right specialist and streams the answer live." },
  { href: "/courses", icon: "🗺️", title: "Course Roadmaps", desc: "Paste a YouTube playlist → a step-by-step quest with summaries, Q&A, and quizzes." },
  { href: "/study", icon: "🧪", title: "Study Tools", desc: "Solve a problem from a photo, or build a knowledge base and ask grounded, cited questions." },
  { href: "/video", icon: "🎬", title: "Video RAG", desc: "Add a YouTube link or upload a local video, then ask questions with timestamp citations." },
  { href: "/code", icon: "💻", title: "Code Playground", desc: "Write code, run it in a sandbox, and get an AI code review." },
  { href: "/arcade", icon: "🎮", title: "Arcade", desc: "XP, streaks, badges, leaderboard, and games built from your own material." },
  { href: "/plan", icon: "📝", title: "Study Plan + PDF", desc: "A multi-agent crew builds a personalized plan you can download as a PDF." },
  { href: "/progress", icon: "📊", title: "My Progress", desc: "Charts of mastery, XP, streaks, and your tracked weak spots." },
];

export default function Dashboard() {
  const { user } = useAuth();
  return (
    <div className="px-8 py-10">
      <h1 className="font-display text-3xl font-bold">
        Welcome, {user?.display_name} 👋
      </h1>
      <p className="mt-2 text-quest-muted">Pick a quest from the sidebar, or jump in below.</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK.map((q) => (
          <Link
            key={q.href}
            href={q.href}
            className="rounded-2xl border border-quest-muted/20 bg-quest-surface p-5 transition-colors hover:border-quest-cyan"
          >
            <h2 className="font-display text-lg font-semibold text-quest-cyan">
              {q.icon} {q.title}
            </h2>
            <p className="mt-2 text-sm text-quest-muted">{q.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
