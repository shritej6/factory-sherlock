/** Mid-tone colours chosen to stay legible on both the light and dark surfaces. */
export const SERIES_COLORS = ['#2f6db5', '#3b8f5f', '#b7791f', '#8a5fb5', '#c2553f', '#4a8f9c'];

export const PASS_COLOR = '#3b8f5f';
export const FAIL_COLOR = '#c2553f';
export const REFERENCE_COLOR = '#8b949e';
export const GRID_COLOR = 'rgba(128, 136, 148, 0.25)';
/** Read at render through the CSS variable so axes follow the active theme. */
export const AXIS_COLOR = 'var(--color-ink-muted)';
export const AXIS_LINE_COLOR = 'var(--color-border)';

export const STATUS_SERIES_COLORS: Record<string, string> = {
  PLANNED: '#8b949e',
  RELEASED: '#2f6db5',
  IN_PROGRESS: '#b7791f',
  COMPLETED: '#3b8f5f',
  CANCELLED: '#c2553f',
};

export function seriesColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length];
}

export const TOOLTIP_STYLE = {
  backgroundColor: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 6,
  color: 'var(--color-ink)',
  fontSize: 12,
};
