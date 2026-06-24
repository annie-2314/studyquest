"use client";
import { motion } from "framer-motion";

const STEPS = [
  { n: "1", title: "Pick a course", desc: "Paste a YouTube playlist or choose a topic to learn." },
  { n: "2", title: "Follow the roadmap", desc: "Step through videos, quizzes, and code challenges." },
  { n: "3", title: "Level up", desc: "Earn XP, keep your streak, and master your weak spots." },
];

export default function HowItWorks() {
  return (
    <section id="how" className="px-6 py-20 md:px-12">
      <h2 className="text-center font-display text-3xl font-bold md:text-4xl">How it works</h2>
      <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-3">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="rounded-2xl bg-gradient-to-b from-quest-surface to-transparent p-6 text-center"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-quest-violet font-display text-xl font-bold">
              {s.n}
            </div>
            <h3 className="mt-4 font-display text-lg font-semibold">{s.title}</h3>
            <p className="mt-2 text-sm text-quest-muted">{s.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
