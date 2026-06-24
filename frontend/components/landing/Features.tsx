"use client";
import { motion } from "framer-motion";

const FEATURES = [
  { title: "Concept Explainer", desc: "Clear explanations with real-life examples for any topic." },
  { title: "Practice Questions", desc: "Adaptive quizzes that get harder as you improve." },
  { title: "Video RAG", desc: "Ask questions about any video with timestamp citations." },
  { title: "Progress Tracker", desc: "Mastery and weak spots tracked across every session." },
  { title: "Resource Finder", desc: "Curated extra resources when you need to go deeper." },
  { title: "Game Master", desc: "XP, streaks, badges, and boss-battle quiz challenges." },
  { title: "Code Reviewer", desc: "In-browser code, run it, get a real review for coding courses." },
];

export default function Features() {
  return (
    <section className="px-6 py-20 md:px-12">
      <h2 className="text-center font-display text-3xl font-bold md:text-4xl">
        Seven specialist agents, one tutor
      </h2>
      <div className="mx-auto mt-12 grid max-w-5xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.05 }}
            className="rounded-2xl border border-quest-muted/15 bg-quest-surface p-6 hover:border-quest-cyan/50"
          >
            <h3 className="font-display text-lg font-semibold text-quest-cyan">{f.title}</h3>
            <p className="mt-2 text-sm text-quest-muted">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
