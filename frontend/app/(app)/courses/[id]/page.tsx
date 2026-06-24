"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { coursesApi, Course, Step } from "@/lib/courses";

export default function CourseRoadmap() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const refresh = () => coursesApi.get(params.id).then(setCourse).catch(() => {});
  useEffect(() => {
    if (user) refresh();
  }, [user, params.id]);

  if (loading || !user || !course) return <main className="p-10 text-quest-muted">Loading…</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/courses" className="text-sm text-quest-cyan">← All courses</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">{course.title}</h1>
      <p className="mt-2 text-sm text-quest-muted">
        {course.completed_steps}/{course.total_steps} done · est. {course.estimated_total}
        {course.proficient && <span className="ml-2 text-quest-lime">🏆 Proficient!</span>}
      </p>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-quest-bg">
        <div className="h-full bg-quest-lime transition-all" style={{ width: `${course.percent}%` }} />
      </div>

      <ol className="mt-8 space-y-3">
        {course.steps.map((s) => (
          <StepCard
            key={s.id}
            courseId={course.id}
            step={s}
            open={openId === s.id}
            onToggle={() => setOpenId(openId === s.id ? null : s.id)}
            onChanged={refresh}
          />
        ))}
      </ol>
    </main>
  );
}

function StepCard({
  courseId,
  step,
  open,
  onToggle,
  onChanged,
}: {
  courseId: string;
  step: Step;
  open: boolean;
  onToggle: () => void;
  onChanged: () => void;
}) {
  const [summary, setSummary] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [quiz, setQuiz] = useState<{ question: string; options: string[] } | null>(null);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState("");

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    try {
      await fn();
    } finally {
      setBusy("");
    }
  }

  return (
    <li className="rounded-2xl border border-quest-muted/20 bg-quest-surface">
      <button onClick={onToggle} className="flex w-full items-center gap-3 p-4 text-left">
        <span
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs ${
            step.completed ? "bg-quest-lime text-quest-bg" : "bg-quest-bg text-quest-muted"
          }`}
        >
          {step.completed ? "✓" : step.ordinal + 1}
        </span>
        <span className="flex-1">
          <span className="block text-sm">{step.title}</span>
          <span className="block text-xs text-quest-muted">
            {step.duration} · est. {step.estimated} {step.quiz_passed && "· quiz ✓"}
          </span>
        </span>
        <span className="text-quest-muted">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-quest-muted/10 p-4">
          <div className="flex flex-wrap gap-2 text-sm">
            <a
              href={step.youtube_url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-quest-muted/30 px-3 py-1.5 hover:border-quest-cyan"
            >
              ▶ Watch
            </a>
            <button
              onClick={() => run("sum", async () => setSummary((await coursesApi.summarize(courseId, step.id)).summary))}
              className="rounded-lg border border-quest-muted/30 px-3 py-1.5 hover:border-quest-cyan"
            >
              {busy === "sum" ? "…" : "Summarize"}
            </button>
            <button
              onClick={() => run("quiz", async () => { setQuiz(await coursesApi.quiz(courseId, step.id)); setFeedback(""); })}
              className="rounded-lg border border-quest-muted/30 px-3 py-1.5 hover:border-quest-cyan"
            >
              {busy === "quiz" ? "…" : "Quiz me"}
            </button>
            {!step.completed && (
              <button
                onClick={() => run("done", async () => { await coursesApi.complete(courseId, step.id); onChanged(); })}
                className="rounded-lg bg-quest-violet px-3 py-1.5"
              >
                Mark complete
              </button>
            )}
          </div>

          {summary && <pre className="whitespace-pre-wrap rounded-xl bg-quest-bg p-3 text-sm">{summary}</pre>}

          <div className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about this video…"
              className="flex-1 rounded-lg border border-quest-muted/30 bg-quest-bg px-3 py-2 text-sm outline-none focus:border-quest-cyan"
            />
            <button
              onClick={() => run("ask", async () => setAnswer((await coursesApi.ask(courseId, step.id, question)).answer))}
              disabled={!question.trim()}
              className="rounded-lg bg-quest-violet px-4 py-2 text-sm disabled:opacity-50"
            >
              {busy === "ask" ? "…" : "Ask"}
            </button>
          </div>
          {answer && <pre className="whitespace-pre-wrap rounded-xl bg-quest-bg p-3 text-sm">{answer}</pre>}

          {quiz && (
            <div className="rounded-xl bg-quest-bg p-3">
              <p className="text-sm font-medium">{quiz.question}</p>
              <div className="mt-2 space-y-2">
                {quiz.options.map((opt, i) => (
                  <button
                    key={i}
                    onClick={() =>
                      run("grade", async () => {
                        const r = await coursesApi.grade(courseId, step.id, quiz.question, opt);
                        setFeedback(r.feedback);
                        if (r.correct) onChanged();
                      })
                    }
                    className="block w-full rounded-lg border border-quest-muted/30 px-3 py-2 text-left text-sm hover:border-quest-cyan"
                  >
                    {opt}
                  </button>
                ))}
              </div>
              {feedback && (
                <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-quest-surface p-3 text-sm">{feedback}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  );
}
