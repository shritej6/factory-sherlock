import type { Inspection, OrderStatus, ResultRow } from '@/types/api';
import { ORDER_STATUSES } from '@/types/constants';

export interface DailyTrendPoint {
  date: string;
  [machineCode: string]: number | string;
}

export interface DailyTrend {
  points: DailyTrendPoint[];
  machines: string[];
}

/** Pivots daily_production_trend rows (one per date and machine) into one point per date. */
export function pivotDailyTrend(rows: ResultRow[]): DailyTrend {
  const byDate = new Map<string, DailyTrendPoint>();
  const machines = new Set<string>();
  for (const row of rows) {
    const date = String(row.production_date ?? '');
    const machine = String(row.machine_code ?? '');
    if (!date || !machine) continue;
    machines.add(machine);
    const point = byDate.get(date) ?? { date };
    point[machine] = Number(row.units_produced ?? 0);
    byDate.set(date, point);
  }
  const sortedMachines = [...machines].sort();
  const points = [...byDate.values()]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((point) => {
      for (const machine of sortedMachines) point[machine] ??= 0;
      return point;
    });
  return { points, machines: sortedMachines };
}

export interface DefectRatePoint {
  machine: string;
  defectRate: number;
  inspected: number;
  failed: number;
  fleetRate: number;
}

export function toDefectRateSeries(rows: ResultRow[]): DefectRatePoint[] {
  return rows
    .map((row) => ({
      machine: String(row.machine_code ?? ''),
      defectRate: Number(row.defect_rate ?? 0),
      inspected: Number(row.inspected ?? 0),
      failed: Number(row.failed ?? 0),
      fleetRate: Number(row.fleet_defect_rate ?? 0),
    }))
    .filter((point) => point.machine !== '')
    .sort((a, b) => a.machine.localeCompare(b.machine));
}

export interface CountPoint {
  name: string;
  value: number;
}

export function toPassFailSeries(summary: { passed: number; failed: number }): CountPoint[] {
  return [
    { name: 'Pass', value: summary.passed },
    { name: 'Fail', value: summary.failed },
  ];
}

export function toDefectCategorySeries(rows: ResultRow[]): CountPoint[] {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const code = String(row.defect_code ?? '');
    if (!code) continue;
    totals.set(code, (totals.get(code) ?? 0) + Number(row.occurrences ?? 0));
  }
  return [...totals.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

/** One bar per status that has orders, in lifecycle order; counts come from envelope totals. */
export function toOrderStatusSeries(counts: Partial<Record<OrderStatus, number>>): CountPoint[] {
  return ORDER_STATUSES.filter((status) => (counts[status] ?? 0) > 0).map((status) => ({
    name: status,
    value: counts[status] ?? 0,
  }));
}

export function countInspectionResults(inspections: Pick<Inspection, 'result'>[]): {
  passed: number;
  failed: number;
} {
  let passed = 0;
  let failed = 0;
  for (const inspection of inspections) {
    if (inspection.result === 'PASS') passed += 1;
    else failed += 1;
  }
  return { passed, failed };
}

export interface ControlChartPoint {
  batchId: number;
  batch: string;
  machine: string;
  subgroupStart: string;
  sampleCount: number;
  mean: number;
  /** Null when the subgroup has a single sample. */
  stdDev: number | null;
  min: number;
  max: number;
  /** True when the mean lies outside the control limits; always false while the limits are null. */
  outOfControl: boolean;
}

export interface ControlChartLimits {
  grandMean: number | null;
  ucl: number | null;
  lcl: number | null;
  target: number | null;
  lowerSpec: number | null;
  upperSpec: number | null;
}

export interface ControlChartSeries {
  points: ControlChartPoint[];
  limits: ControlChartLimits;
  /** Y axis bounds padded around the control limits, the specification limits, and the means. */
  domain: [number, number];
  /** Evenly spaced round tick values that span the domain. */
  ticks: number[];
}

function numberOrNull(value: ResultRow[string] | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function toControlChartPoint(row: ResultRow, limits: ControlChartLimits): ControlChartPoint {
  const mean = numberOrNull(row.mean_value) ?? 0;
  const aboveUcl = limits.ucl !== null && mean > limits.ucl;
  const belowLcl = limits.lcl !== null && mean < limits.lcl;
  return {
    batchId: Number(row.batch_id ?? 0),
    batch: String(row.batch_number ?? ''),
    machine: String(row.machine_code ?? ''),
    subgroupStart: String(row.subgroup_start ?? ''),
    sampleCount: Number(row.sample_count ?? 0),
    mean,
    stdDev: numberOrNull(row.std_dev),
    min: numberOrNull(row.min_value) ?? mean,
    max: numberOrNull(row.max_value) ?? mean,
    outOfControl: aboveUcl || belowLcl,
  };
}

/** A 1, 2, 5, or 10 multiple of a power of ten that divides the range into about six steps. */
function niceStep(range: number): number {
  const rough = range / 6;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return factor * magnitude;
}

/** Removes the floating point noise left by multiplying a step such as 0.05. */
function roundToStep(value: number, step: number): number {
  const decimals = Math.max(0, Math.ceil(-Math.log10(step)) + 1);
  return Number(value.toFixed(decimals));
}

interface ControlChartAxis {
  domain: [number, number];
  ticks: number[];
}

/**
 * Pads the axis so every limit and every plotted mean sits inside the chart with room to spare,
 * then widens it to round tick values so the axis labels read well.
 */
export function controlChartAxis(
  points: Pick<ControlChartPoint, 'mean'>[],
  limits: ControlChartLimits,
): ControlChartAxis {
  const values = [
    limits.lcl,
    limits.ucl,
    limits.lowerSpec,
    limits.upperSpec,
    ...points.map((point) => point.mean),
  ].filter((value): value is number => value !== null);
  if (values.length === 0) return { domain: [0, 1], ticks: [0, 1] };
  const low = Math.min(...values);
  const high = Math.max(...values);
  const padding = high === low ? Math.max(Math.abs(high) * 0.01, 0.01) : (high - low) * 0.1;
  const step = niceStep(high - low + 2 * padding);
  const epsilon = 1e-9;
  const start = roundToStep(Math.floor((low - padding) / step + epsilon) * step, step);
  const end = roundToStep(Math.ceil((high + padding) / step - epsilon) * step, step);
  const ticks: number[] = [];
  for (let tick = start; tick <= end + step / 2; tick += step) ticks.push(roundToStep(tick, step));
  return { domain: [start, end], ticks };
}

export function controlChartDomain(
  points: Pick<ControlChartPoint, 'mean'>[],
  limits: ControlChartLimits,
): [number, number] {
  return controlChartAxis(points, limits).domain;
}

/** Maps characteristic_control_chart rows (one per batch) to points; the limits repeat on every row. */
export function toControlChartSeries(rows: ResultRow[]): ControlChartSeries {
  const first = rows[0];
  const limits: ControlChartLimits = {
    grandMean: numberOrNull(first?.grand_mean),
    ucl: numberOrNull(first?.ucl),
    lcl: numberOrNull(first?.lcl),
    target: numberOrNull(first?.target_value),
    lowerSpec: numberOrNull(first?.lower_spec_limit),
    upperSpec: numberOrNull(first?.upper_spec_limit),
  };
  const points = rows.map((row) => toControlChartPoint(row, limits));
  return { points, limits, ...controlChartAxis(points, limits) };
}

/** The leading hyphen-delimited segments every batch number shares, so ticks show only what differs. */
export function sharedBatchPrefix(batches: string[]): string {
  if (batches.length < 2) return '';
  let prefix = batches[0];
  for (const batch of batches.slice(1)) {
    let index = 0;
    while (index < prefix.length && prefix[index] === batch[index]) index += 1;
    prefix = prefix.slice(0, index);
  }
  const cut = prefix.lastIndexOf('-');
  return cut === -1 ? '' : prefix.slice(0, cut + 1);
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

function sideOf(mean: number, grandMean: number): 'above' | 'below' | 'on' {
  if (mean > grandMean) return 'above';
  return mean < grandMean ? 'below' : 'on';
}

/** The trailing run of at least three subgroups on one side of the grand mean, if the run has a start. */
function trailingRun(
  points: ControlChartPoint[],
  grandMean: number,
): { start: ControlChartPoint; side: 'above' | 'below' } | null {
  const last = points.at(-1);
  if (!last) return null;
  const side = sideOf(last.mean, grandMean);
  if (side === 'on') return null;
  let startIndex = points.length - 1;
  while (startIndex > 0 && sideOf(points[startIndex - 1].mean, grandMean) === side) startIndex -= 1;
  if (points.length - startIndex < 3 || startIndex === 0) return null;
  return { start: points[startIndex], side };
}

/**
 * One plain sentence about the plotted window. It says where the points sit relative to the
 * limits and the grand mean; it does not say why.
 */
export function describeControlChart(series: ControlChartSeries): string {
  const { points, limits } = series;
  if (points.length === 0) return 'No subgroups fall inside the selected window.';
  const { ucl, lcl, grandMean } = limits;
  if (ucl === null || lcl === null || grandMean === null) {
    return 'Control limits are not available because every subgroup in the window has a single sample.';
  }
  const above = points.filter((point) => point.mean > ucl).length;
  const below = points.filter((point) => point.mean < lcl).length;
  const total = plural(points.length, 'subgroup');
  const clauses = [
    above + below === 0
      ? `All ${total} fall inside the control limits`
      : `${above + below} of ${total} fall outside the control limits (${below} below the lower limit, ${above} above the upper limit)`,
  ];
  const run = trailingRun(points, grandMean);
  if (run) {
    clauses.push(
      `the subgroup mean runs ${run.side} the grand mean from batch ${run.start.batch} onward`,
    );
  }
  return `${clauses.join('; ')}.`;
}
