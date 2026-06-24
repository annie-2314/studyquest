"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Home", icon: "🏠" },
  { href: "/chat", label: "Chat Tutor", icon: "💬" },
  { href: "/study", label: "Study Tools", icon: "🧪" },
  { href: "/courses", label: "Course Roadmaps", icon: "🗺️" },
  { href: "/code", label: "Code Playground", icon: "💻" },
  { href: "/video", label: "Video RAG", icon: "🎬" },
  { href: "/arcade", label: "Arcade", icon: "🎮" },
  { href: "/plan", label: "Study Plan + PDF", icon: "📝" },
  { href: "/progress", label: "My Progress", icon: "📊" },
  { href: "/insights", label: "Insights & Eval", icon: "🔬" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-quest-muted/15 bg-quest-surface">
      <Link href="/dashboard" className="block px-6 py-5 font-display text-xl font-bold">
        Study<span className="text-quest-lime">Quest</span> AI
      </Link>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-quest-violet/30 text-quest-text"
                  : "text-quest-muted hover:bg-quest-bg hover:text-quest-text"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-quest-muted/15 p-4">
        {user && <p className="mb-2 truncate text-sm text-quest-text">{user.display_name}</p>}
        <button
          onClick={logout}
          className="w-full rounded-xl border border-quest-muted/30 px-3 py-2 text-sm text-quest-muted hover:border-quest-cyan hover:text-quest-text"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
