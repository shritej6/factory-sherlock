import type { ReactNode } from 'react';

import { ResultRowsTable } from '@/components/ui/DataTable';
import { EmptyState } from '@/components/ui/States';
import type { ResultRow } from '@/types/api';

interface ChartFrameProps {
  title: string;
  description?: string;
  empty: boolean;
  emptyTitle?: string;
  height?: number;
  /** The plotted rows, offered as a table for readers who cannot use the chart. */
  tableRows?: ResultRow[];
  /** Charts placed directly under the page heading use h2; charts inside a titled section use h3. */
  headingLevel?: 'h2' | 'h3';
  children: ReactNode;
}

/** Shared wrapper so every chart carries a heading, a description, an empty state, and a data table. */
export function ChartFrame({
  title,
  description,
  empty,
  emptyTitle = 'No data for this window',
  height = 260,
  tableRows,
  headingLevel: Heading = 'h2',
  children,
}: ChartFrameProps) {
  const imageLabel = [title, description].filter(Boolean).join('. ');
  return (
    <figure className="panel p-4">
      <figcaption className="mb-3">
        <Heading className="text-sm font-semibold text-ink">{title}</Heading>
        {description && <p className="text-xs text-ink-muted">{description}</p>}
      </figcaption>
      {empty ? (
        <EmptyState title={emptyTitle} />
      ) : (
        <>
          <div style={{ height }} role="img" aria-label={imageLabel}>
            {children}
          </div>
          {tableRows && tableRows.length > 0 && (
            <details className="mt-3 border-t border-border pt-3">
              <summary className="cursor-pointer text-xs font-medium text-accent hover:underline">
                View data table
              </summary>
              <div className="mt-2">
                <ResultRowsTable rows={tableRows} caption={`${title} data`} />
              </div>
            </details>
          )}
        </>
      )}
    </figure>
  );
}
