/**
 * Chart colours for the black field. Series step from amber through white to grey so a chart
 * stays monochrome apart from the one accent; pass and fail keep the state colours.
 */
export const SERIES_COLORS = ['#ffb000', '#ededed', '#8a8a8a', '#f2c75c', '#c9c9c9', '#5c5c5c'];

export const PASS_COLOR = '#43c56d';
export const FAIL_COLOR = '#ff4a3d';
export const REFERENCE_COLOR = '#8a8a8a';
/** Specification limits on the control chart, kept apart from the grey control limits. */
export const SPEC_LIMIT_COLOR = '#ffb000';
export const GRID_COLOR = 'rgba(255, 255, 255, 0.08)';
/** Read at render through the CSS variable so axes follow the theme tokens. */
export const AXIS_COLOR = 'var(--color-ink-muted)';
export const AXIS_LINE_COLOR = 'var(--color-border-strong)';

export const STATUS_SERIES_COLORS: Record<string, string> = {
  PLANNED: '#8a8a8a',
  RELEASED: '#ededed',
  IN_PROGRESS: '#ffb000',
  COMPLETED: '#43c56d',
  CANCELLED: '#ff4a3d',
};

export function seriesColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length];
}

export const TOOLTIP_STYLE = {
  backgroundColor: 'var(--color-surface)',
  border: '1px solid var(--color-border-strong)',
  borderRadius: 0,
  color: 'var(--color-ink)',
  fontSize: 12,
};
