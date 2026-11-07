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
