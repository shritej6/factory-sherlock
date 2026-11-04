import { useId, useState } from 'react';

interface SqlDisclosureProps {
  sql: string;
  queryName: string;
  params?: Record<string, string | number | null>;
}

export function SqlDisclosure({ sql, queryName, params }: SqlDisclosureProps) {
  const [open, setOpen] = useState(false);
  const regionId = useId();
  return (
    <div className="mt-3 border-t border-border pt-3">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={regionId}
        onClick={() => setOpen((value) => !value)}
        className="text-xs font-medium text-accent hover:underline"
      >
        {open ? 'Hide the SQL' : 'Show the SQL'}
      </button>
      {open && (
        <div id={regionId} className="mt-2">
          <p className="mb-1 text-xs text-ink-muted">
            Query name: <code className="font-mono text-ink">{queryName}</code>
          </p>
          {params && Object.keys(params).length > 0 && (
            <p className="mb-2 text-xs text-ink-muted">
              Parameters:{' '}
              <code className="font-mono text-ink">
                {Object.entries(params)
                  .map(([key, value]) => `${key}=${value ?? 'null'}`)
                  .join(', ')}
              </code>
            </p>
          )}
          <pre className="max-h-80 overflow-auto rounded-panel border border-border bg-surface-muted p-3 font-mono text-xs leading-relaxed whitespace-pre text-ink">
            {sql}
          </pre>
        </div>
      )}
    </div>
  );
}
