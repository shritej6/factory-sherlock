export function Chip({ children }: { children: string }) {
  return (
    <span className="inline-flex items-center border border-border bg-surface-muted px-1.5 py-0.5 font-mono text-[11px] text-ink">
      {children}
    </span>
  );
}
