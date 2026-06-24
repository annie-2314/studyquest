"use client";
import { motion } from "framer-motion";

export default function DemoPreview() {
  return (
    <section className="px-6 py-20 md:px-12">
      <div className="mx-auto max-w-4xl rounded-3xl border border-quest-muted/15 bg-quest-surface p-8">
        <h2 className="font-display text-2xl font-bold">Your roadmap, gamified</h2>
        <p className="mt-2 text-sm text-quest-muted">
          A preview of a course roadmap (interactive in later phases).
        </p>
        <div className="mt-6 space-y-3">
          {["Intro & setup", "Core concepts", "Hands-on project", "Final boss quiz"].map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className={`h-4 w-4 rounded-full ${i === 0 ? "bg-quest-lime" : "bg-quest-muted/30"}`} />
              <span className={i === 0 ? "text-quest-text" : "text-quest-muted"}>{step}</span>
            </div>
          ))}
        </div>
        <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-quest-bg">
          <motion.div
            initial={{ width: 0 }}
            whileInView={{ width: "25%" }}
            viewport={{ once: true }}
            transition={{ duration: 1 }}
            className="h-full bg-quest-lime"
          />
        </div>
        <p className="mt-2 text-xs text-quest-muted">25% complete · 1 of 4 steps</p>
      </div>
    </section>
  );
}
