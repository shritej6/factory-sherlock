interface StatTileProps {
  label: string;
  /** Leave undefined while the figure is loading; the tile then announces that it is loading. */
  value?: string;
  detail?: string;
}

export function StatTile({ label, value, detail }: StatTileProps) {
  return (
    <div className="panel px-4 py-3" aria-busy={value === undefined || undefined}>
      <p className="text-xs font-medium tracking-wide text-ink-muted uppercase">{label}</p>
      {value === undefined ? (
        <p className="mt-1 text-2xl font-semibold text-ink-muted">
          <span aria-hidden="true">...</span>
          <span className="sr-only">Loading</span>
        </p>
      ) : (
        <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
      )}
      {detail && <p className="mt-0.5 text-xs text-ink-faint">{detail}</p>}
    </div>
  );
}
