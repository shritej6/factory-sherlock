import type { DotItemDotProps, TooltipPayload } from 'recharts';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { ControlChartPoint, ControlChartSeries } from '@/utils/chartTransforms';
import { sharedBatchPrefix } from '@/utils/chartTransforms';
import {
  AXIS_COLOR,
  AXIS_LINE_COLOR,
  FAIL_COLOR,
  GRID_COLOR,
  REFERENCE_COLOR,
  SPEC_LIMIT_COLOR,
  seriesColor,
  TOOLTIP_STYLE,
} from '@/utils/chartTheme';
import { formatDateTime, formatMeasure } from '@/utils/format';

import { ChartFrame } from './ChartFrame';

const MEAN_COLOR = seriesColor(0);
const CONTROL_LIMIT_DASH = '6 4';
const SPEC_LIMIT_DASH = '2 3';
const MAX_TICKS = 12;

interface ControlChartProps {
  series: ControlChartSeries;
  unit: string;
  title?: string;
  description?: string;
}

/** Show at most MAX_TICKS labels; Recharts' interval is the number of ticks skipped between labels. */
function tickInterval(count: number): number {
  return Math.max(0, Math.ceil(count / MAX_TICKS) - 1);
}

function isControlChartPoint(value: unknown): value is ControlChartPoint {
  return typeof value === 'object' && value !== null && 'batch' in value && 'mean' in value;
}

function MeanDot({ cx, cy, payload }: DotItemDotProps) {
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

function ControlChartTooltip({
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
  const rows: Array<[string, string]> = [
    ['Batch', point.batch],
    ['Machine', point.machine],
    ['Started', formatDateTime(point.subgroupStart)],
    ['n', String(point.sampleCount)],
    ['Mean', `${formatMeasure(point.mean)} ${unit}`],
    ['Std dev', point.stdDev === null ? 'n/a (one sample)' : formatMeasure(point.stdDev)],
    ['Min', formatMeasure(point.min)],
    ['Max', formatMeasure(point.max)],
  ];
  return (
    <div style={TOOLTIP_STYLE} className="px-3 py-2">
      {point.outOfControl && (
        <p className="mb-1 font-medium" style={{ color: FAIL_COLOR }}>
          Outside the control limits
        </p>
      )}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        {rows.map(([label, value]) => (
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

function ControlChartLegend({ hasControlLimits }: { hasControlLimits: boolean }) {
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
            Control limits (UCL, LCL)
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

function toTableRow(point: ControlChartPoint) {
  return {
    batch_number: point.batch,
    machine_code: point.machine,
    subgroup_start: point.subgroupStart,
    sample_count: point.sampleCount,
    mean_value: point.mean,
    std_dev: point.stdDev,
    min_value: point.min,
    max_value: point.max,
    outside_control_limits: point.outOfControl,
  };
}

/** X-bar chart: one subgroup per batch, with control limits from the window and the specification limits. */
export function ControlChart({
  series,
  unit,
  title = 'Control chart',
  description,
}: ControlChartProps) {
  const { points, limits, domain, ticks } = series;
  const prefix = sharedBatchPrefix(points.map((point) => point.batch));
  const hasControlLimits = limits.ucl !== null && limits.lcl !== null;
  return (
    <ChartFrame
      title={title}
      description={description}
      empty={points.length === 0}
      emptyTitle="No inspections of this characteristic in the window"
      height={340}
      tableRows={points.map(toTableRow)}
      headingLevel="h3"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} vertical={false} />
          <XAxis
            dataKey="batch"
            interval={tickInterval(points.length)}
            tickFormatter={(value) => String(value).slice(prefix.length)}
            tick={{ fill: AXIS_COLOR, fontSize: 11 }}
            axisLine={{ stroke: AXIS_LINE_COLOR }}
            tickLine={false}
          />
          <YAxis
            domain={domain}
            ticks={ticks}
            tickFormatter={(value) => formatMeasure(value)}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={64}
          />
          <Tooltip
            cursor={{ stroke: GRID_COLOR }}
            content={({ active, payload }) => (
              <ControlChartTooltip active={active} payload={payload} unit={unit} />
            )}
          />
          <Legend content={() => <ControlChartLegend hasControlLimits={hasControlLimits} />} />
          {limits.lowerSpec !== null && (
            <ReferenceLine
              y={limits.lowerSpec}
              stroke={SPEC_LIMIT_COLOR}
              strokeDasharray={SPEC_LIMIT_DASH}
              className="control-chart-spec-limit"
            />
          )}
          {limits.upperSpec !== null && (
            <ReferenceLine
              y={limits.upperSpec}
              stroke={SPEC_LIMIT_COLOR}
              strokeDasharray={SPEC_LIMIT_DASH}
              className="control-chart-spec-limit"
            />
          )}
          {hasControlLimits && (
            <ReferenceLine
              y={limits.lcl ?? 0}
              stroke={REFERENCE_COLOR}
              strokeDasharray={CONTROL_LIMIT_DASH}
              className="control-chart-control-limit"
            />
          )}
          {hasControlLimits && (
            <ReferenceLine
              y={limits.ucl ?? 0}
              stroke={REFERENCE_COLOR}
              strokeDasharray={CONTROL_LIMIT_DASH}
              className="control-chart-control-limit"
            />
          )}
          {limits.grandMean !== null && (
            <ReferenceLine
              y={limits.grandMean}
              stroke={REFERENCE_COLOR}
              className="control-chart-grand-mean"
            />
          )}
          <Line
            type="linear"
            dataKey="mean"
            stroke={MEAN_COLOR}
            strokeWidth={1.5}
            dot={(props: DotItemDotProps) => <MeanDot key={`dot-${props.index}`} {...props} />}
            activeDot={{ r: 6, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
