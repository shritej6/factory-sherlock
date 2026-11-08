interface StatTileProps {
  label: string;
  /** Leave undefined while the figure is loading; the tile then announces that it is loading. */
  value?: string;
  detail?: string;
}

/** An instrument readout: the figure large in the condensed face, its label beneath. */
export function StatTile({ label, value, detail }: StatTileProps) {
  return (
    <div
      className="panel flex flex-col-reverse justify-end px-4 py-3"
      aria-busy={value === undefined || undefined}
    >
      {detail && <p className="mt-0.5 text-xs text-ink-faint">{detail}</p>}
      <p className="mt-1 text-xs text-ink-muted">{label}</p>
      {value === undefined ? (
        <p className="font-display text-[34px] leading-none font-semibold text-ink-muted">
          <span aria-hidden="true">---</span>
          <span className="sr-only">Loading</span>
        </p>
      ) : (
        <p className="font-display text-[34px] leading-none font-semibold text-ink">{value}</p>
      )}
    </div>
  );
}
