"use client";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";

export default function Hero() {
  return (
    <section className="relative overflow-hidden px-6 py-24 text-center md:px-12">
      <motion.div
        className="pointer-events-none absolute left-1/2 top-10 h-72 w-72 -translate-x-1/2 rounded-full bg-quest-violet/30 blur-3xl"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 6, repeat: Infinity }}
      />
      <motion.h1
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="font-display text-5xl font-bold leading-tight md:text-7xl"
      >
        Turn any course into a <span className="text-quest-lime">quest</span>.
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="mx-auto mt-6 max-w-2xl text-lg text-quest-muted"
      >
        An AI tutor that explains anything, turns YouTube courses into trackable roadmaps,
        remembers your weak spots, and levels you up as you learn.
      </motion.p>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.35 }}
        className="mt-10 flex justify-center gap-4"
      >
        <Button href="/signup">Start your quest</Button>
        <Button href="#how" variant="ghost">
          See how it works
        </Button>
      </motion.div>
    </section>
  );
}
