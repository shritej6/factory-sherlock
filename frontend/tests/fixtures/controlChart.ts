import type { ResultRow } from '@/types/api';

/** Limits from the documented Query 10 result for STEEL-SHAFT diameter over the demo window. */
export const CONTROL_CHART_LIMITS = {
  target_value: 20,
  lower_spec_limit: 19.9,
  upper_spec_limit: 20.1,
  grand_mean: 20.0442,
  ucl: 20.0653,
  lcl: 20.0231,
};

/** One characteristic_control_chart row; min and max sit 0.05 either side of the mean. */
export function subgroupRow(
  batchId: number,
  batch: string,
  mean: number,
  overrides: Partial<ResultRow> = {},
): ResultRow {
  return {
    batch_id: batchId,
    batch_number: batch,
    machine_code: 'CNC-03',
    subgroup_start: `2026-11-02T0${batchId}:00:00`,
    sample_count: 20,
    mean_value: mean,
    std_dev: 0.03,
    min_value: Number((mean - 0.05).toFixed(4)),
    max_value: Number((mean + 0.05).toFixed(4)),
    ...CONTROL_CHART_LIMITS,
    ...overrides,
  };
}

/** Six of the twelve demo subgroups: two below the LCL, two inside, two above the UCL. */
export function controlChartRows(overrides: Partial<ResultRow> = {}): ResultRow[] {
  return [
    subgroupRow(1, 'SIM0001-CNC-03-01-B01', 19.9906, {
      std_dev: 0.0406,
      min_value: 19.914,
      max_value: 20.065,
      ...overrides,
    }),
    subgroupRow(2, 'SIM0001-CNC-03-01-B02', 20.009, overrides),
    subgroupRow(3, 'SIM0001-CNC-03-02-B03', 20.0426, overrides),
    subgroupRow(4, 'SIM0001-CNC-03-02-B04', 20.047, overrides),
    subgroupRow(5, 'SIM0001-CNC-03-03-B01', 20.0758, overrides),
    subgroupRow(6, 'SIM0001-CNC-03-03-B04', 20.1301, overrides),
  ];
}

export const CONTROL_CHART_ROWS: ResultRow[] = controlChartRows();
