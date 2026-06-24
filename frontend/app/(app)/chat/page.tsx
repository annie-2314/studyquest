"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { chatWsUrl } from "@/lib/ws";

interface ChatMessage {
  role: "user" | "assistant";
  agent?: string;
  content: string;
}

export default function ChatPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const convRef = useRef<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  // Open the WebSocket once authenticated.
  useEffect(() => {
    if (!user) return;
    const ws = new WebSocket(chatWsUrl());
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "route") {
        // Start a fresh assistant bubble labeled with the routed agent.
        setMessages((m) => [...m, { role: "assistant", agent: msg.agent, content: "" }]);
      } else if (msg.type === "token") {
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          if (last && last.role === "assistant") last.content += msg.data;
          return copy;
        });
      } else if (msg.type === "done") {
        convRef.current = msg.conversation_id;
        setStreaming(false);
      } else if (msg.type === "error") {
        setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${msg.detail}` }]);
        setStreaming(false);
      }
    };
    return () => ws.close();
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function send() {
    const text = input.trim();
    if (!text || streaming || !connected) return;
    const token = localStorage.getItem("sq_access");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setStreaming(true);
    wsRef.current?.send(
      JSON.stringify({ token, message: text, conversation_id: convRef.current })
    );
  }

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col px-4">
      <header className="flex items-center justify-between py-4">
        <Link href="/dashboard" className="font-display text-lg font-bold">
          Study<span className="text-quest-lime">Quest</span> · Tutor
        </Link>
        <span className={`text-xs ${connected ? "text-quest-lime" : "text-quest-muted"}`}>
          {connected ? "● live" : "○ connecting"}
        </span>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messages.length === 0 && (
          <p className="mt-10 text-center text-quest-muted">
            Ask me to explain anything, or say &quot;quiz me on …&quot;.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            {m.agent && <p className="mb-1 text-xs text-quest-cyan">{m.agent}</p>}
            <div
              className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm ${
                m.role === "user"
                  ? "bg-quest-violet text-white"
                  : "bg-quest-surface text-quest-text"
              }`}
            >
              {m.content || <span className="opacity-50">…</span>}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 py-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask your tutor…"
          className="flex-1 rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-quest-text outline-none focus:border-quest-cyan"
        />
        <button
          onClick={send}
          disabled={streaming || !connected}
          className="rounded-xl bg-quest-violet px-6 py-3 font-display font-medium disabled:opacity-50"
        >
          {streaming ? "…" : "Send"}
        </button>
      </div>
    </main>
  );
}
