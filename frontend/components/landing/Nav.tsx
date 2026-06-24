import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function Nav() {
  return (
    <nav className="flex items-center justify-between px-6 py-5 md:px-12">
      <Link href="/" className="font-display text-xl font-bold">
        Study<span className="text-quest-lime">Quest</span> AI
      </Link>
      <div className="flex items-center gap-3">
        <Link href="/login" className="text-quest-muted hover:text-quest-text">
          Log in
        </Link>
        <Button href="/signup">Start your quest</Button>
      </div>
    </nav>
  );
}
