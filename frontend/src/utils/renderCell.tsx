import type { ReactNode } from 'react';

import { formatDateTime, formatNumber, formatPercent } from './format';

const DATETIME_PATTERN = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/;
const RATE_KEY = /(^|_)(rate|share)(_|$)|_change$/;

/** Formats an untyped SQL result value for display; rate-like columns become percentages. */
export function renderCell(value: unknown, key?: string): ReactNode {
  if (value === null || value === undefined) return <span className="text-ink-faint">null</span>;
  if (typeof value === 'number') {
    if (key && RATE_KEY.test(key) && Math.abs(value) <= 1) return formatPercent(value);
    return formatNumber(value);
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'string' && DATETIME_PATTERN.test(value)) return formatDateTime(value);
  return String(value);
}
