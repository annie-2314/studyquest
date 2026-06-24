"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";

interface StudentRow {
  user: { display_name: string; email: string };
  xp: number;
  level: number;
  streak: number;
  completed_steps: number;
  quizzes_passed: number;
  weak_spots: string[];
}

const tok = () => localStorage.getItem("sq_access") ?? undefined;

export default function TeacherPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [rows, setRows] = useState<StudentRow[]>([]);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (user) {
      apiFetch<StudentRow[]>("/analytics/students", {}, tok())
        .then(setRows)
        .catch((e) => {
          if (e instanceof ApiError && e.status === 403) setDenied(true);
        });
    }
  }, [user]);

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">Teacher Dashboard</h1>

      {denied ? (
        <p className="mt-6 rounded-xl bg-quest-surface p-4 text-sm text-quest-muted">
          This view is for <strong>teacher</strong> or <strong>parent</strong> accounts. Sign up with
          that role to monitor students.
        </p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-2xl border border-quest-muted/20 bg-quest-surface">
          <table className="w-full text-left text-sm">
            <thead className="text-quest-muted">
              <tr className="border-b border-quest-muted/10">
                <th className="p-3">Student</th>
                <th className="p-3">Level</th>
                <th className="p-3">XP</th>
                <th className="p-3">Streak</th>
                <th className="p-3">Steps</th>
                <th className="p-3">Quizzes</th>
                <th className="p-3">Weak spots</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-quest-muted/5">
                  <td className="p-3">{r.user.display_name}</td>
                  <td className="p-3">{r.level}</td>
                  <td className="p-3">{r.xp}</td>
                  <td className="p-3">{r.streak}🔥</td>
                  <td className="p-3">{r.completed_steps}</td>
                  <td className="p-3">{r.quizzes_passed}</td>
                  <td className="p-3 text-quest-muted">{r.weak_spots.slice(0, 3).join(", ") || "—"}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={7} className="p-4 text-center text-quest-muted">No students yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
