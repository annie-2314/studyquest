export function Input(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-quest-muted">{label}</span>
      <input
        {...rest}
        className="w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-quest-text outline-none focus:border-quest-cyan"
      />
    </label>
  );
}
