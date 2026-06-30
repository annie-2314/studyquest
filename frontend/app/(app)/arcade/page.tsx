"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import Markdown from "@/components/Markdown";

interface Badge { key: string; emoji: string; name: string; earned: boolean; }
interface Profile {
  xp: number; level: number; xp_into_level: number; xp_per_level: number;
  streak: number; longest_streak: number; badges: Badge[];
}
interface LbRow { display_name: string; xp: number; level: number; streak: number; }
interface Card { front: string; back: string; }
interface BossQ { q: string; options: string[]; answer_index: number; }
interface Source { id: string; title: string; kind: string; }

const tok = () => localStorage.getItem("sq_access") ?? undefined;
const URL_OPT = "__url__";          // sentinel: "paste a web URL" dropdown choice
const INTEREST_KEY = "sq_interest"; // what the learner likes (for tailored examples)
const XP_PER_CORRECT = 5;

export default function Learn() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [board, setBoard] = useState<LbRow[]>([]);
  const [topic, setTopic] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceId, setSourceId] = useState("");  // "" = typed topic; URL_OPT = url entry; else doc id

  // web-URL source entry
  const [urlInput, setUrlInput] = useState("");
  const [urlBusy, setUrlBusy] = useState(false);
  const [urlError, setUrlError] = useState("");

  // learner interest (persisted) — powers personalised explanations
  const [interest, setInterest] = useState("");
  const [askInterest, setAskInterest] = useState(false);
  const [interestDraft, setInterestDraft] = useState("");
  const pendingExplain = useRef<((i: string) => void) | null>(null);

  // understand-this-material panels
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [studyExplain, setStudyExplain] = useState<string | null>(null);
  const [studyBusy, setStudyBusy] = useState(false);

  const [cards, setCards] = useState<Card[]>([]);
  const [flipped, setFlipped] = useState<number | null>(null);

  // quiz — continuous flow with per-question feedback
  const [boss, setBoss] = useState<BossQ[]>([]);
  const [bossIdx, setBossIdx] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [bossScore, setBossScore] = useState(0);
  const [bossDone, setBossDone] = useState(false);
  const [qExplain, setQExplain] = useState<string | null>(null);
  const [qExplainBusy, setQExplainBusy] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  useEffect(() => {
    setInterest(localStorage.getItem(INTEREST_KEY) ?? "");
  }, []);

  const loadProfile = () => apiFetch<Profile>("/game/profile", {}, tok()).then(setProfile).catch(() => {});
  const loadBoard = () => apiFetch<LbRow[]>("/game/leaderboard", {}, tok()).then(setBoard).catch(() => {});
  const loadSources = () => apiFetch<Source[]>("/game/sources", {}, tok()).then(setSources).catch(() => {});
  useEffect(() => {
    if (user) { loadProfile(); loadBoard(); loadSources(); }
  }, [user]);

  function sourceEmoji(kind: string) {
    return kind === "video" ? "🎬" : kind === "web" ? "🌐" : "📄";
  }

  // The request body: a chosen document drives everything, else the typed topic.
  function gameBody() {
    return sourceId && sourceId !== URL_OPT ? { document_id: sourceId } : { topic };
  }
  function currentTitle() {
    if (sourceId && sourceId !== URL_OPT) return sources.find((s) => s.id === sourceId)?.title ?? topic;
    return topic;
  }
  // Anything chosen to act on? (a real topic or a selected document)
  const ready = (sourceId && sourceId !== URL_OPT) || topic.trim().length > 0;

  async function addUrl() {
    const url = urlInput.trim();
    if (!url || urlBusy) return;
    setUrlBusy(true);
    setUrlError("");
    try {
      const doc = await apiFetch<Source>("/study/documents/url",
        { method: "POST", body: JSON.stringify({ url }) }, tok());
      await loadSources();
      setSourceId(doc.id);   // select the freshly-added page
      setUrlInput("");
      resetPanels();
    } catch (e: any) {
      setUrlError(e?.detail || e?.message || "Could not add that page.");
    } finally {
      setUrlBusy(false);
    }
  }

  function resetPanels() {
    setSummary(null); setStudyExplain(null); setCards([]); setBoss([]); setBossDone(false);
  }

  // ---- interest gate: ask once, then run the queued explanation ----
  function gateInterest(run: (i: string) => void) {
    if (interest) { run(interest); return; }
    pendingExplain.current = run;
    setInterestDraft("");
    setAskInterest(true);
  }
  function saveInterest(skip: boolean) {
    const val = skip ? "" : interestDraft.trim();
    setInterest(val);
    localStorage.setItem(INTEREST_KEY, val);
    setAskInterest(false);
    const run = pendingExplain.current;
    pendingExplain.current = null;
    run?.(val);
  }

  async function runExplain(concept: string, correct: string,
                            setText: (s: string | null) => void,
                            setBusy: (b: boolean) => void, interestVal: string) {
    setBusy(true);
    setText(null);
    try {
      const r = await apiFetch<{ explanation: string }>("/game/explain", {
        method: "POST",
        body: JSON.stringify({ ...gameBody(), concept, correct_answer: correct, interest: interestVal }),
      }, tok());
      setText(r.explanation);
    } catch (e: any) {
      setText(`⚠️ ${e?.detail || "Could not load an explanation."}`);
    } finally {
      setBusy(false);
    }
  }

  // ---- understand-this-material actions ----
  async function doSummarize() {
    setSummaryBusy(true);
    setSummary(null);
    setStudyExplain(null);
    try {
      const r = await apiFetch<{ summary: string }>("/game/summarize",
        { method: "POST", body: JSON.stringify(gameBody()) }, tok());
      setSummary(r.summary);
    } catch (e: any) {
      setSummary(`⚠️ ${e?.detail || "Could not summarise this."}`);
    } finally {
      setSummaryBusy(false);
    }
  }
  function explainTopic() {
    gateInterest((i) => runExplain(currentTitle() || "this topic", "", setStudyExplain, setStudyBusy, i));
  }

  async function getCards() {
    const r = await apiFetch<{ cards: Card[] }>("/game/flashcards",
      { method: "POST", body: JSON.stringify(gameBody()) }, tok());
    setCards(r.cards);
    setFlipped(null);
  }

  async function startQuiz() {
    const r = await apiFetch<{ questions: BossQ[] }>("/game/boss",
      { method: "POST", body: JSON.stringify(gameBody()) }, tok());
    setBoss(r.questions);
    setBossIdx(0);
    setSelected(null);
    setRevealed(false);
    setQExplain(null);
    setBossScore(0);
    setBossDone(false);
  }

  // Pick an answer — reveal right/wrong immediately, but DON'T auto-advance.
  function answer(i: number) {
    if (revealed) return;
    setSelected(i);
    setRevealed(true);
    const correct = i === boss[bossIdx].answer_index;
    if (correct) setBossScore((s) => s + 1);
    // Knowledge tracing: record this attempt against the current concept.
    const concept = currentTitle().trim();
    if (concept) {
      apiFetch("/learning/attempt", {
        method: "POST", body: JSON.stringify({ concept, correct }),
      }, tok()).catch(() => {});
    }
  }
  async function next() {
    if (bossIdx + 1 < boss.length) {
      setBossIdx((n) => n + 1);
      setSelected(null);
      setRevealed(false);
      setQExplain(null);
    } else {
      setBossDone(true);
      const gained = bossScore * XP_PER_CORRECT;
      if (gained > 0) {
        await apiFetch("/game/xp",
          { method: "POST", body: JSON.stringify({ amount: gained, reason: "quiz" }) }, tok());
        loadProfile();
        loadBoard();
      }
    }
  }
  function explainQuestion() {
    const q = boss[bossIdx];
    gateInterest((i) => runExplain(q.q, q.options[q.answer_index], setQExplain, setQExplainBusy, i));
  }

  function optionClasses(i: number) {
    const base = "block w-full rounded-lg border px-3 py-2 text-left text-sm transition";
    if (!revealed) return `${base} border-quest-muted/30 hover:border-quest-cyan cursor-pointer`;
    const correct = i === boss[bossIdx].answer_index;
    if (correct) return `${base} border-quest-lime bg-quest-lime/15 text-quest-lime`;
    if (i === selected) return `${base} border-red-500 bg-red-500/15 text-red-300`;
    return `${base} border-quest-muted/20 opacity-60`;
  }

  if (loading || !user || !profile) return <main className="p-10 text-quest-muted">Loading...</main>;

  const pct = Math.round((100 * profile.xp_into_level) / profile.xp_per_level);
  const usingUrl = sourceId === URL_OPT;
  const current = boss[bossIdx];

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">📚 Learn</h1>
      <p className="mt-1 text-sm text-quest-muted">
        Bring a topic, an upload, or a web link — get a summary, an explanation tuned to what you
        love, and a quiz to lock it in.
      </p>

      {/* Slim progress strip (gamification kept, but not the headline) */}
      <div className="mt-4 flex items-center gap-3 rounded-xl border border-quest-muted/15 bg-quest-surface px-4 py-2 text-xs text-quest-muted">
        <span className="font-medium text-quest-text">Lv {profile.level}</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-quest-bg">
          <div className="h-full bg-quest-lime" style={{ width: `${pct}%` }} />
        </div>
        <span>{profile.xp} XP · 🔥 {profile.streak}d</span>
      </div>

      {/* Source picker — the hero control */}
      <div className="mt-5 space-y-2">
        <select
          value={sourceId}
          onChange={(e) => { setSourceId(e.target.value); setUrlError(""); resetPanels(); }}
          className="w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
        >
          <option value="">Type a topic</option>
          <option value={URL_OPT}>🌐 Paste a web URL…</option>
          {sources.length > 0 && <option disabled>— or use my material —</option>}
          {sources.map((s) => (
            <option key={s.id} value={s.id}>{sourceEmoji(s.kind)} {s.title}</option>
          ))}
        </select>

        {usingUrl ? (
          <div className="space-y-1">
            <div className="flex gap-2">
              <input
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addUrl()}
                placeholder="https://… (article, tutorial, W3Schools page)"
                className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
              />
              <button onClick={addUrl} disabled={urlBusy || !urlInput.trim()}
                className="rounded-xl bg-quest-cyan/90 px-4 py-2 text-sm font-medium text-quest-bg disabled:opacity-50">
                {urlBusy ? "Fetching…" : "Add page"}
              </button>
            </div>
            {urlError && <p className="text-xs text-red-400">{urlError}</p>}
            <p className="text-xs text-quest-muted/70">We&apos;ll read the page text, then you can learn from it below.</p>
          </div>
        ) : (
          !sourceId && (
            <input
              value={topic}
              onChange={(e) => { setTopic(e.target.value); }}
              placeholder="e.g. fractions, photosynthesis, agentic AI"
              className="w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
            />
          )
        )}

        {/* Action row */}
        {!usingUrl && (
          <div className="flex flex-wrap gap-2 pt-1">
            <button onClick={doSummarize} disabled={!ready || summaryBusy}
              className="rounded-xl border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan disabled:opacity-40">
              {summaryBusy ? "Reading…" : "📝 Summarize"}
            </button>
            <button onClick={explainTopic} disabled={!ready || studyBusy}
              className="rounded-xl border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan disabled:opacity-40">
              {studyBusy ? "Thinking…" : "💡 Explain it"}
            </button>
            <button onClick={getCards} disabled={!ready}
              className="rounded-xl border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan disabled:opacity-40">
              🃏 Flashcards
            </button>
            <button onClick={startQuiz} disabled={!ready}
              className="rounded-xl bg-quest-violet px-4 py-2 text-sm disabled:opacity-40">
              ⚔️ Quiz me
            </button>
          </div>
        )}

        <p className="text-xs text-quest-muted/70">
          {interest
            ? <>Examples tuned to <span className="text-quest-cyan">{interest}</span>{" "}
                <button onClick={() => { localStorage.removeItem(INTEREST_KEY); setInterest(""); }} className="underline">change</button></>
            : <>Add material in <Link href="/study" className="text-quest-cyan">Study Tools</Link> or{" "}
                <Link href="/video" className="text-quest-cyan">Video RAG</Link>, or paste a URL above.</>}
        </p>
      </div>

      {/* Interest gate (shared by all explanations) */}
      {askInterest && (
        <div className="mt-4 rounded-xl border border-quest-cyan/30 bg-quest-bg p-3">
          <p className="text-sm">What do you enjoy? I&apos;ll build the example around it.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <input
              value={interestDraft}
              onChange={(e) => setInterestDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveInterest(false)}
              placeholder="e.g. football, cooking, video games"
              className="flex-1 rounded-lg border border-quest-muted/30 bg-quest-surface px-3 py-1.5 text-sm outline-none focus:border-quest-cyan"
            />
            <button onClick={() => saveInterest(false)} className="rounded-lg bg-quest-cyan/90 px-3 py-1.5 text-sm font-medium text-quest-bg">Use this</button>
            <button onClick={() => saveInterest(true)} className="rounded-lg border border-quest-muted/30 px-3 py-1.5 text-sm">Skip</button>
          </div>
        </div>
      )}

      {/* Summary + standalone explanation */}
      {summary && (
        <div className="mt-4 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5 text-sm">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-quest-cyan">What this is</p>
          <Markdown>{summary}</Markdown>
        </div>
      )}
      {studyExplain && (
        <div className="mt-4 rounded-2xl border border-quest-muted/20 bg-quest-surface p-5 text-sm">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-quest-cyan">In depth</p>
          <Markdown>{studyExplain}</Markdown>
        </div>
      )}

      {/* Flashcards */}
      {cards.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {cards.map((c, i) => (
            <button key={i} onClick={() => setFlipped(flipped === i ? null : i)}
              className="h-28 rounded-xl border border-quest-muted/20 bg-quest-surface p-3 text-sm hover:border-quest-cyan">
              {flipped === i ? <span className="text-quest-lime">{c.back}</span> : c.front}
            </button>
          ))}
        </div>
      )}

      {/* Quiz — continuous, with clear feedback + Explain */}
      {boss.length > 0 && !bossDone && current && (
        <div className="mt-4 rounded-2xl border border-quest-violet/40 bg-quest-surface p-6">
          <div className="flex items-center justify-between text-xs text-quest-muted">
            <span>Question {bossIdx + 1} / {boss.length}</span>
            <span className="font-medium text-quest-lime">Score {bossScore} · {bossScore * XP_PER_CORRECT} XP</span>
          </div>
          <p className="mt-2 font-medium">{current.q}</p>

          <div className="mt-3 space-y-2">
            {current.options.map((o, i) => (
              <button key={i} onClick={() => answer(i)} disabled={revealed} className={optionClasses(i)}>
                <span className="mr-2">
                  {revealed && i === current.answer_index ? "✓" : revealed && i === selected ? "✗" : "•"}
                </span>
                {o}
              </button>
            ))}
          </div>

          {revealed && (
            <div className="mt-4">
              <p className={`text-sm font-medium ${selected === current.answer_index ? "text-quest-lime" : "text-red-400"}`}>
                {selected === current.answer_index ? "✅ Correct!" : "❌ Not quite — the highlighted answer is right."}
              </p>

              {qExplain && (
                <div className="mt-3 rounded-xl border border-quest-muted/20 bg-quest-bg p-3 text-sm">
                  <Markdown>{qExplain}</Markdown>
                </div>
              )}

              <div className="mt-3 flex gap-2">
                <button onClick={explainQuestion} disabled={qExplainBusy}
                  className="rounded-lg border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan disabled:opacity-50">
                  {qExplainBusy ? "Thinking…" : qExplain ? "Explain again" : "💡 Explain"}
                </button>
                <button onClick={next} className="rounded-lg bg-quest-violet px-5 py-2 text-sm font-medium">
                  {bossIdx + 1 < boss.length ? "Next →" : "Finish"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      {bossDone && (
        <div className="mt-4 rounded-2xl border border-quest-lime/40 bg-quest-surface p-6 text-center">
          <p className="font-display text-2xl">🏆 {bossScore} / {boss.length}</p>
          <p className="mt-2 text-sm text-quest-muted">+{bossScore * XP_PER_CORRECT} XP earned!</p>
          <button onClick={startQuiz} className="mt-4 rounded-xl bg-quest-violet px-5 py-2 text-sm font-medium">Play again</button>
        </div>
      )}

      {/* Achievements */}
      <section className="mt-8">
        <h2 className="font-display text-lg font-semibold">Achievements</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {profile.badges.map((b) => (
            <span key={b.key} title={b.name}
              className={`rounded-full px-3 py-1 text-sm ${b.earned ? "bg-quest-violet/30 text-quest-text" : "bg-quest-surface text-quest-muted/40"}`}>
              {b.emoji} {b.name}
            </span>
          ))}
        </div>
      </section>

      {/* Leaderboard */}
      <section className="mt-8">
        <h2 className="font-display text-lg font-semibold">Leaderboard</h2>
        <ol className="mt-3 space-y-2">
          {board.map((r, i) => (
            <li key={i} className="flex items-center justify-between rounded-xl bg-quest-surface px-4 py-2 text-sm">
              <span>{i + 1}. {r.display_name}</span>
              <span className="text-quest-muted">Lv {r.level} · {r.xp} XP</span>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
