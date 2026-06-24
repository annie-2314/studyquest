"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

interface Badge { key: string; emoji: string; name: string; earned: boolean; }
interface Profile {
  xp: number; level: number; xp_into_level: number; xp_per_level: number;
  streak: number; longest_streak: number; badges: Badge[];
}
interface LbRow { display_name: string; xp: number; level: number; streak: number; }
interface Card { front: string; back: string; }
interface BossQ { q: string; options: string[]; answer_index: number; }

const tok = () => localStorage.getItem("sq_access") ?? undefined;

export default function Arcade() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [board, setBoard] = useState<LbRow[]>([]);
  const [topic, setTopic] = useState("fractions");
  const [cards, setCards] = useState<Card[]>([]);
  const [flipped, setFlipped] = useState<number | null>(null);
  const [boss, setBoss] = useState<BossQ[]>([]);
  const [bossIdx, setBossIdx] = useState(0);
  const [bossScore, setBossScore] = useState(0);
  const [bossDone, setBossDone] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const loadProfile = () => apiFetch<Profile>("/game/profile", {}, tok()).then(setProfile).catch(() => {});
  const loadBoard = () => apiFetch<LbRow[]>("/game/leaderboard", {}, tok()).then(setBoard).catch(() => {});
  useEffect(() => {
    if (user) { loadProfile(); loadBoard(); }
  }, [user]);

  async function getCards() {
    const r = await apiFetch<{ cards: Card[] }>("/game/flashcards", { method: "POST", body: JSON.stringify({ topic }) }, tok());
    setCards(r.cards);
    setFlipped(null);
  }

  async function startBoss() {
    const r = await apiFetch<{ questions: BossQ[] }>("/game/boss", { method: "POST", body: JSON.stringify({ topic }) }, tok());
    setBoss(r.questions);
    setBossIdx(0);
    setBossScore(0);
    setBossDone(false);
  }

  async function answerBoss(i: number) {
    const correct = i === boss[bossIdx].answer_index;
    const score = bossScore + (correct ? 1 : 0);
    setBossScore(score);
    if (bossIdx + 1 < boss.length) {
      setBossIdx(bossIdx + 1);
    } else {
      setBossDone(true);
      await apiFetch("/game/xp", { method: "POST", body: JSON.stringify({ amount: score * 5, reason: "boss battle" }) }, tok());
      loadProfile();
      loadBoard();
    }
  }

  if (loading || !user || !profile) return <main className="p-10 text-quest-muted">Loading...</main>;

  const pct = Math.round((100 * profile.xp_into_level) / profile.xp_per_level);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/dashboard" className="text-sm text-quest-cyan">← Dashboard</Link>
      <h1 className="mt-4 font-display text-3xl font-bold">🎮 Arcade</h1>

      {/* Profile */}
      <section className="mt-6 rounded-2xl border border-quest-muted/20 bg-quest-surface p-6">
        <div className="flex items-center justify-between">
          <span className="font-display text-xl">Level {profile.level}</span>
          <span className="text-sm text-quest-muted">{profile.xp} XP · 🔥 {profile.streak}-day streak</span>
        </div>
        <div className="mt-3 h-3 w-full overflow-hidden rounded-full bg-quest-bg">
          <div className="h-full bg-quest-lime transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {profile.badges.map((b) => (
            <span
              key={b.key}
              title={b.name}
              className={`rounded-full px-3 py-1 text-sm ${b.earned ? "bg-quest-violet/30 text-quest-text" : "bg-quest-bg text-quest-muted/40"}`}
            >
              {b.emoji} {b.name}
            </span>
          ))}
        </div>
      </section>

      {/* Topic control */}
      <div className="mt-6 flex gap-2">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Topic for mini-games"
          className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-2 text-sm outline-none focus:border-quest-cyan"
        />
        <button onClick={getCards} className="rounded-xl border border-quest-muted/30 px-4 py-2 text-sm hover:border-quest-cyan">Flashcards</button>
        <button onClick={startBoss} className="rounded-xl bg-quest-violet px-4 py-2 text-sm">Boss battle</button>
      </div>

      {/* Flashcards */}
      {cards.length > 0 && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {cards.map((c, i) => (
            <button
              key={i}
              onClick={() => setFlipped(flipped === i ? null : i)}
              className="h-28 rounded-xl border border-quest-muted/20 bg-quest-surface p-3 text-sm hover:border-quest-cyan"
            >
              {flipped === i ? <span className="text-quest-lime">{c.back}</span> : c.front}
            </button>
          ))}
        </div>
      )}

      {/* Boss battle */}
      {boss.length > 0 && !bossDone && (
        <div className="mt-6 rounded-2xl border border-quest-violet/40 bg-quest-surface p-6">
          <p className="text-xs text-quest-muted">Question {bossIdx + 1} / {boss.length}</p>
          <p className="mt-1 font-medium">{boss[bossIdx].q}</p>
          <div className="mt-3 space-y-2">
            {boss[bossIdx].options.map((o, i) => (
              <button key={i} onClick={() => answerBoss(i)} className="block w-full rounded-lg border border-quest-muted/30 px-3 py-2 text-left text-sm hover:border-quest-cyan">
                {o}
              </button>
            ))}
          </div>
        </div>
      )}
      {bossDone && (
        <div className="mt-6 rounded-2xl border border-quest-lime/40 bg-quest-surface p-6 text-center">
          <p className="font-display text-2xl">🏆 {bossScore} / {boss.length}</p>
          <p className="mt-2 text-sm text-quest-muted">+{bossScore * 5} XP earned!</p>
        </div>
      )}

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
