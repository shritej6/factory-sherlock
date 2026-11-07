import { useEffect } from 'react';
import type { ReactNode } from 'react';

import type { PageState } from '@/hooks/usePageState';
import { PAGE_SIZES } from '@/types/constants';
import { formatNumber } from '@/utils/format';

import { Button } from './Button';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (page: PageState) => void;
  /** Names the list for assistive technology, for example "Production orders". */
  label: string;
  pageSizes?: readonly number[];
  className?: string;
}

/** The offset of the last page that still holds a row. */
function lastPageOffset(total: number, limit: number): number {
  return Math.floor((total - 1) / limit) * limit;
}

function PageSizeSelect({
  limit,
  pageSizes,
  onChange,
}: Pick<PaginationProps, 'limit' | 'onChange'> & { pageSizes: readonly number[] }) {
  const sizes = pageSizes.includes(limit) ? pageSizes : [...pageSizes, limit].sort((a, b) => a - b);
  return (
    <label className="flex items-center gap-1.5">
      <span>Rows per page</span>
      <select
        className="field-input w-auto py-1 text-xs"
        value={limit}
        onChange={(event) => onChange({ limit: Number(event.target.value), offset: 0 })}
      >
        {sizes.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>
    </label>
  );
}

function PageButtons({ total, limit, offset, onChange }: Omit<PaginationProps, 'label'>) {
  return (
    <div className="flex items-center gap-1.5">
      <Button
        size="sm"
        disabled={offset === 0}
        aria-label="Previous page"
        onClick={() => onChange({ limit, offset: Math.max(0, offset - limit) })}
      >
        Previous
      </Button>
      <Button
        size="sm"
        disabled={offset + limit >= total}
        aria-label="Next page"
        onClick={() => onChange({ limit, offset: offset + limit })}
      >
        Next
      </Button>
    </div>
  );
}

/**
 * Range text, previous and next buttons, and a page-size selector for one paged list.
 * When the offset runs past the total (the last page emptied after a delete, or the total
 * shrank) the component shows and requests the last page that still has rows.
 */
export function Pagination({
  total,
  limit,
  offset,
  onChange,
  label,
  pageSizes = PAGE_SIZES,
  className = '',
}: PaginationProps) {
  const overrun = total > 0 && offset >= total;
  const shownOffset = overrun ? lastPageOffset(total, limit) : offset;
  useEffect(() => {
    if (overrun) onChange({ limit, offset: shownOffset });
  }, [overrun, limit, shownOffset, onChange]);
  if (total === 0) return null;
  const from = shownOffset + 1;
  const to = Math.min(shownOffset + limit, total);
  return (
    <nav
      aria-label={`${label} pagination`}
      className={`flex flex-wrap items-center justify-between gap-3 border-t border-border py-2 text-xs text-ink-muted ${className}`}
    >
      <p aria-live="polite">
        {`Showing ${formatNumber(from)} to ${formatNumber(to)} of ${formatNumber(total)}`}
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <PageSizeSelect limit={limit} pageSizes={pageSizes} onChange={onChange} />
        <PageButtons total={total} limit={limit} offset={shownOffset} onChange={onChange} />
      </div>
    </nav>
  );
}

/** Keeps the previous page visible but dimmed while the next page loads. */
export function PageBody({ loading, children }: { loading: boolean; children: ReactNode }) {
  return (
    <div
      aria-busy={loading || undefined}
      className={loading ? 'opacity-60 transition-opacity motion-reduce:transition-none' : ''}
    >
      {children}
    </div>
  );
}
