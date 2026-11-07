import type { DotItemDotProps, TooltipPayload } from 'recharts';

import type { ControlChartPoint } from '@/utils/chartTransforms';
import {
  FAIL_COLOR,
  REFERENCE_COLOR,
  seriesColor,
  SPEC_LIMIT_COLOR,
  TOOLTIP_STYLE,
} from '@/utils/chartTheme';
import { formatDateTime, formatMeasure } from '@/utils/format';

export const MEAN_COLOR = seriesColor(0);
export const CONTROL_LIMIT_DASH = '6 4';
export const SPEC_LIMIT_DASH = '2 3';

function isControlChartPoint(value: unknown): value is ControlChartPoint {
  return typeof value === 'object' && value !== null && 'batch' in value && 'mean' in value;
}

export function MeanDot({ cx, cy, payload }: DotItemDotProps) {
  if (cx === undefined || cy === undefined || !isControlChartPoint(payload)) return null;
  const out = payload.outOfControl;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={out ? 5 : 3}
      fill={out ? FAIL_COLOR : MEAN_COLOR}
      stroke="var(--color-surface)"
      strokeWidth={1}
      className={out ? 'control-chart-dot control-chart-dot-out' : 'control-chart-dot'}
      data-out-of-control={out ? 'true' : 'false'}
    />
  );
}

/** Label and value pairs for one subgroup; the limits are listed only when the subgroup has them. */
function tooltipRows(point: ControlChartPoint, unit: string): Array<[string, string]> {
  const limits: Array<[string, string]> =
    point.ucl !== null && point.lcl !== null
      ? [
          ['UCL', `${formatMeasure(point.ucl)} ${unit}`],
          ['LCL', `${formatMeasure(point.lcl)} ${unit}`],
        ]
      : [];
  return [
    ['Batch', point.batch],
    ['Machine', point.machine],
    ['Started', formatDateTime(point.subgroupStart)],
    ['n', String(point.sampleCount)],
    ['Mean', `${formatMeasure(point.mean)} ${unit}`],
    ...limits,
    ['Std dev', point.stdDev === null ? 'n/a (one sample)' : formatMeasure(point.stdDev)],
    ['Min', formatMeasure(point.min)],
    ['Max', formatMeasure(point.max)],
  ];
}

export function ControlChartTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean;
  payload?: TooltipPayload;
  unit: string;
}) {
  const point: unknown = payload?.[0]?.payload;
  if (!active || !isControlChartPoint(point)) return null;
  return (
    <div style={TOOLTIP_STYLE} className="px-3 py-2">
      {point.outOfControl && (
        <p className="mb-1 font-medium" style={{ color: FAIL_COLOR }}>
          Outside the control limits
        </p>
      )}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        {tooltipRows(point, unit).map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-ink-muted">{label}</dt>
            <dd className="font-mono">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function LegendSwatch({ color, dash }: { color: string; dash?: string }) {
  return (
    <svg width="28" height="8" aria-hidden="true" className="shrink-0">
      <line x1="0" y1="4" x2="28" y2="4" stroke={color} strokeWidth="2" strokeDasharray={dash} />
    </svg>
  );
}

export function ControlChartLegend({ hasControlLimits }: { hasControlLimits: boolean }) {
  return (
    <ul className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-ink-muted">
      <li className="flex items-center gap-1.5">
        <svg width="28" height="8" aria-hidden="true" className="shrink-0">
          <line x1="0" y1="4" x2="28" y2="4" stroke={MEAN_COLOR} strokeWidth="1.5" />
          <circle cx="14" cy="4" r="3" fill={MEAN_COLOR} />
        </svg>
        Subgroup mean
      </li>
      <li className="flex items-center gap-1.5">
        <svg width="28" height="8" aria-hidden="true" className="shrink-0">
          <circle cx="14" cy="4" r="4" fill={FAIL_COLOR} />
        </svg>
        Outside control limits
      </li>
      {hasControlLimits && (
        <>
          <li className="flex items-center gap-1.5">
            <LegendSwatch color={REFERENCE_COLOR} />
            Grand mean
          </li>
          <li className="flex items-center gap-1.5">
            <LegendSwatch color={REFERENCE_COLOR} dash={CONTROL_LIMIT_DASH} />
            Control limits (UCL, LCL), per subgroup
          </li>
        </>
      )}
      <li className="flex items-center gap-1.5">
        <LegendSwatch color={SPEC_LIMIT_COLOR} dash={SPEC_LIMIT_DASH} />
        Specification limits
      </li>
    </ul>
  );
}
