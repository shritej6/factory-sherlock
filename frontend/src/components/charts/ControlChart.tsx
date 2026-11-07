import type { DotItemDotProps } from 'recharts';
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

import type {
  ControlChartLimits,
  ControlChartPoint,
  ControlChartSeries,
} from '@/utils/chartTransforms';
import { sharedBatchPrefix } from '@/utils/chartTransforms';
import {
  AXIS_COLOR,
  AXIS_LINE_COLOR,
  GRID_COLOR,
  REFERENCE_COLOR,
  SPEC_LIMIT_COLOR,
} from '@/utils/chartTheme';
import { formatMeasure } from '@/utils/format';

import { ChartFrame } from './ChartFrame';
import {
  CONTROL_LIMIT_DASH,
  ControlChartLegend,
  ControlChartTooltip,
  MEAN_COLOR,
  MeanDot,
  SPEC_LIMIT_DASH,
} from './ControlChartParts';

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
    ucl: point.ucl,
    lcl: point.lcl,
    outside_control_limits: point.outOfControl,
  };
}

/** Batch numbers along the bottom with their shared prefix removed, measured values on the left. */
function ControlChartAxes({
  points,
  domain,
  ticks,
}: Omit<ControlChartSeries, 'limits' | 'hasControlLimits'>) {
  const prefix = sharedBatchPrefix(points.map((point) => point.batch));
  return (
    <>
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
    </>
  );
}

/** The specification limits and the grand mean hold one value for the whole window. */
function WindowReferenceLines({ limits }: { limits: ControlChartLimits }) {
  return (
    <>
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
      {limits.grandMean !== null && (
        <ReferenceLine
          y={limits.grandMean}
          stroke={REFERENCE_COLOR}
          className="control-chart-grand-mean"
        />
      )}
    </>
  );
}

/** UCL and LCL step from subgroup to subgroup because each depends on its own sample count. */
function ControlLimitSteps() {
  return (
    <>
      {(['ucl', 'lcl'] as const).map((key) => (
        <Line
          key={key}
          type="stepAfter"
          dataKey={key}
          stroke={REFERENCE_COLOR}
          strokeDasharray={CONTROL_LIMIT_DASH}
          dot={false}
          activeDot={false}
          isAnimationActive={false}
          className="control-chart-control-limit"
        />
      ))}
    </>
  );
}

/** The hover card and the legend, which explain the series rather than draw them. */
function ChartAnnotations({ unit, hasControlLimits }: { unit: string; hasControlLimits: boolean }) {
  return (
    <>
      <Tooltip
        cursor={{ stroke: GRID_COLOR }}
        content={({ active, payload }) => (
          <ControlChartTooltip active={active} payload={payload} unit={unit} />
        )}
      />
      <Legend content={() => <ControlChartLegend hasControlLimits={hasControlLimits} />} />
    </>
  );
}

/** X-bar chart: one subgroup per batch, with per-subgroup control limits and the specification limits. */
export function ControlChart({
  series,
  unit,
  title = 'Control chart',
  description,
}: ControlChartProps) {
  const { points, limits, hasControlLimits, domain, ticks } = series;
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
          <ControlChartAxes points={points} domain={domain} ticks={ticks} />
          <ChartAnnotations unit={unit} hasControlLimits={hasControlLimits} />
          <WindowReferenceLines limits={limits} />
          {hasControlLimits && <ControlLimitSteps />}
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
