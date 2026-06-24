import Link from "next/link";

export function Button({
  href,
  children,
  variant = "primary",
}: {
  href: string;
  children: React.ReactNode;
  variant?: "primary" | "ghost";
}) {
  const base =
    "inline-flex items-center justify-center rounded-xl px-6 py-3 font-display font-medium transition-transform hover:scale-105";
  const styles =
    variant === "primary"
      ? "bg-quest-violet text-white shadow-lg shadow-quest-violet/30"
      : "border border-quest-muted/40 text-quest-text hover:border-quest-cyan";
  return (
    <Link href={href} className={`${base} ${styles}`}>
      {children}
    </Link>
  );
}
