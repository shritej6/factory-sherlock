const numberFormat = new Intl.NumberFormat('en-US');

/** API datetimes are naive ISO strings; show them as "YYYY-MM-DD HH:MM". */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '';
  const [date, time = ''] = value.replace(' ', 'T').split('T');
  return time ? `${date} ${time.slice(0, 5)}` : date;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '';
  return value.slice(0, 10);
}

export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '';
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? numberFormat.format(numeric) : String(value);
}

export function formatPercent(fraction: number | string | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined || fraction === '') return '';
  const numeric = typeof fraction === 'number' ? fraction : Number(fraction);
  if (!Number.isFinite(numeric)) return String(fraction);
  return `${(numeric * 100).toFixed(digits)}%`;
}

/** Converts a datetime-local input value to the seconds-precision ISO form the API expects. */
export function toApiDateTime(local: string): string {
  if (!local) return local;
  return local.length === 16 ? `${local}:00` : local;
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/** Turns snake_case column names into readable table headers. */
export function humanizeKey(key: string): string {
  return key.replace(/_/g, ' ');
}
