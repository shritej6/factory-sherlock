import { describe, expect, it } from 'vitest';

import {
  countInspectionResults,
  pivotDailyTrend,
  toDefectCategorySeries,
  toDefectRateSeries,
  toOrderStatusSeries,
  toPassFailSeries,
} from './chartTransforms';

describe('pivotDailyTrend', () => {
  it('pivots one row per date and machine into one point per date, filling gaps with zero', () => {
    const trend = pivotDailyTrend([
      {
        production_date: '2026-11-03',
        machine_code: 'CNC-02',
        units_produced: 100,
        units_failed: 1,
      },
      {
        production_date: '2026-11-02',
        machine_code: 'CNC-01',
        units_produced: 240,
        units_failed: 2,
      },
      {
        production_date: '2026-11-02',
        machine_code: 'CNC-02',
        units_produced: 220,
        units_failed: 3,
      },
    ]);
    expect(trend.machines).toEqual(['CNC-01', 'CNC-02']);
    expect(trend.points).toEqual([
      { date: '2026-11-02', 'CNC-01': 240, 'CNC-02': 220 },
      { date: '2026-11-03', 'CNC-01': 0, 'CNC-02': 100 },
    ]);
  });

  it('returns no points for an empty result', () => {
    expect(pivotDailyTrend([])).toEqual({ points: [], machines: [] });
  });
});

describe('category transforms', () => {
  it('builds the defect-rate series sorted by machine code', () => {
    const series = toDefectRateSeries([
      {
        machine_code: 'CNC-03',
        defect_rate: 0.0958,
        inspected: 480,
        failed: 46,
        fleet_defect_rate: 0.0364,
      },
      {
        machine_code: 'CNC-01',
        defect_rate: 0.0042,
        inspected: 480,
        failed: 2,
        fleet_defect_rate: 0.0364,
      },
    ]);
    expect(series.map((p) => p.machine)).toEqual(['CNC-01', 'CNC-03']);
    expect(series[1]).toMatchObject({ defectRate: 0.0958, failed: 46, fleetRate: 0.0364 });
  });

  it('sums defect occurrences across machines and sorts them descending', () => {
    expect(
      toDefectCategorySeries([
        { machine_code: 'CNC-03', defect_code: 'OVERSIZE_DIAMETER', occurrences: 45 },
        { machine_code: 'CNC-01', defect_code: 'OVERSIZE_DIAMETER', occurrences: 2 },
        { machine_code: 'CNC-01', defect_code: 'DIMENSIONAL_DEVIATION', occurrences: 5 },
      ]),
    ).toEqual([
      { name: 'OVERSIZE_DIAMETER', value: 47 },
      { name: 'DIMENSIONAL_DEVIATION', value: 5 },
    ]);
  });

  it('counts orders by status and inspections by result', () => {
    expect(toOrderStatusSeries({ COMPLETED: 2, IN_PROGRESS: 1, PLANNED: 0 })).toEqual([
      { name: 'IN_PROGRESS', value: 1 },
      { name: 'COMPLETED', value: 2 },
    ]);
    expect(
      countInspectionResults([{ result: 'PASS' }, { result: 'FAIL' }, { result: 'PASS' }]),
    ).toEqual({ passed: 2, failed: 1 });
    expect(toPassFailSeries({ passed: 1349, failed: 51 })).toEqual([
      { name: 'Pass', value: 1349 },
      { name: 'Fail', value: 51 },
    ]);
  });
});
