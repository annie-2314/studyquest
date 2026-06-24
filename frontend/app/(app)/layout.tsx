"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Sidebar from "@/components/Sidebar";

// Shared shell for all authenticated pages: persistent left sidebar + a
// scrollable main content area in the middle. Centralizes the auth guard.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <main className="p-10 text-quest-muted">Loading…</main>;
  }

  return (
    <div className="flex">
      <Sidebar />
      <main className="h-screen flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
