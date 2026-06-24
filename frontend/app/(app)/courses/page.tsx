"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { coursesApi, Course } from "@/lib/courses";

export default function CoursesPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (user) coursesApi.list().then(setCourses).catch(() => {});
  }, [user]);

  async function create() {
    setError("");
    setBusy(true);
    try {
      const c = await coursesApi.create(url.trim());
      router.push(`/courses/${c.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Could not create course");
    } finally {
      setBusy(false);
    }
  }

  async function loadDemo() {
    setError("");
    setBusy(true);
    try {
      const c = await coursesApi.demo();
      router.push(`/courses/${c.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Could not load sample course");
    } finally {
      setBusy(false);
    }
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Course Roadmaps</h1>
      <p className="mt-2 text-sm text-quest-muted">
        Paste a YouTube <strong>playlist</strong> link — we turn it into a step-by-step quest.
      </p>

      <div className="mt-6 flex gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/playlist?list=…"
          className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-sm outline-none focus:border-quest-cyan"
        />
        <button
          onClick={create}
          disabled={busy || !url.trim()}
          className="rounded-xl bg-quest-violet px-6 py-3 font-display text-sm disabled:opacity-50"
        >
          {busy ? "Building…" : "Build roadmap"}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}

      <button
        onClick={loadDemo}
        disabled={busy}
        className="mt-3 text-sm text-quest-cyan underline-offset-2 hover:underline disabled:opacity-50"
      >
        No YouTube access? Load a sample course →
      </button>

      <div className="mt-8 space-y-3">
        {courses.map((c) => (
          <Link
            key={c.id}
            href={`/courses/${c.id}`}
            className="block rounded-2xl border border-quest-muted/20 bg-quest-surface p-5 hover:border-quest-cyan"
          >
            <div className="flex items-center justify-between">
              <h2 className="font-display font-semibold">{c.title}</h2>
              <span className="text-xs text-quest-muted">{c.percent}% · {c.total_steps} videos</span>
            </div>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-quest-bg">
              <div className="h-full bg-quest-lime" style={{ width: `${c.percent}%` }} />
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
