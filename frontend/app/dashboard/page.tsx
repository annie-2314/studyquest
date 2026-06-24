"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
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
      <p className="mt-3 text-quest-muted">
        Your quest begins in Phase 2 — the AI tutor, roadmaps, and games are on the way.
      </p>
      <button
        onClick={logout}
        className="mt-8 rounded-xl border border-quest-muted/40 px-5 py-2 hover:border-quest-cyan"
      >
        Log out
      </button>
    </main>
  );
}
