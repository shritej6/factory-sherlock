import { describe, expect, it } from 'vitest';

import { CONTROL_CHART_ROWS, controlChartRows, subgroupRow } from '@tests/fixtures/controlChart';

import {
  controlChartAxis,
  controlChartDomain,
  countInspectionResults,
  describeControlChart,
  pivotDailyTrend,
  sharedBatchPrefix,
  toControlChartSeries,
  toDefectCategorySeries,
  toDefectRateSeries,
  toOrderStatusSeries,
  toPassFailSeries,
} from './chartTransforms';

const NO_LIMITS = { ucl: null, lcl: null, lowerSpec: null, upperSpec: null };

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

describe('toControlChartSeries', () => {
  it('maps one row per batch to a point and flags the means outside the control limits', () => {
    const series = toControlChartSeries(CONTROL_CHART_ROWS);
    expect(series.points).toHaveLength(6);
    expect(series.points[0]).toEqual({
      batchId: 1,
      batch: 'SIM0001-CNC-03-01-B01',
      machine: 'CNC-03',
      subgroupStart: '2026-11-02T01:00:00',
      sampleCount: 20,
      mean: 19.9906,
      stdDev: 0.0406,
      min: 19.914,
      max: 20.065,
      outOfControl: true,
    });
    expect(series.points.map((p) => p.outOfControl)).toEqual([
      true,
      true,
      false,
      false,
      true,
      true,
    ]);
    expect(series.limits).toEqual({
      grandMean: 20.0442,
      ucl: 20.0653,
      lcl: 20.0231,
      target: 20,
      lowerSpec: 19.9,
      upperSpec: 20.1,
    });
  });

  it('reads decimals that arrive as strings', () => {
    const series = toControlChartSeries([
      subgroupRow(1, 'B01', 20.2, { mean_value: '20.2000', ucl: '20.0653', std_dev: '0.0300' }),
    ]);
    expect(series.points[0]).toMatchObject({ mean: 20.2, stdDev: 0.03, outOfControl: true });
    expect(series.limits.ucl).toBe(20.0653);
  });

  it('pads the y domain around the limits and the plotted means, on round tick values', () => {
    const series = toControlChartSeries(CONTROL_CHART_ROWS);
    expect(series.domain).toEqual([19.85, 20.2]);
    expect(series.ticks).toEqual([19.85, 19.9, 19.95, 20, 20.05, 20.1, 20.15, 20.2]);
    expect(controlChartDomain([], series.limits)).toEqual([19.85, 20.15]);
    expect(controlChartDomain([{ mean: 5 }], { ...series.limits, lowerSpec: null })).toEqual([
      0, 25,
    ]);
    expect(controlChartAxis([{ mean: 20 }], { ...series.limits, ...NO_LIMITS })).toEqual({
      domain: [19.8, 20.2],
      ticks: [19.8, 19.9, 20, 20.1, 20.2],
    });
  });

  it('handles null control limits and null std_dev without flagging any point', () => {
    const series = toControlChartSeries(controlChartRows({ ucl: null, lcl: null, std_dev: null }));
    expect(series.limits.ucl).toBeNull();
    expect(series.limits.lcl).toBeNull();
    expect(series.points.every((p) => p.stdDev === null)).toBe(true);
    expect(series.points.some((p) => p.outOfControl)).toBe(false);
    expect(series.domain[0]).toBeLessThan(19.9);
    expect(series.domain[1]).toBeGreaterThan(20.1301);
  });

  it('returns an empty series with a default domain for no rows', () => {
    expect(toControlChartSeries([])).toEqual({
      points: [],
      limits: {
        grandMean: null,
        ucl: null,
        lcl: null,
        target: null,
        lowerSpec: null,
        upperSpec: null,
      },
      domain: [0, 1],
      ticks: [0, 1],
    });
  });
});

describe('describeControlChart', () => {
  it('counts the subgroups outside the limits and names the start of a trailing run', () => {
    expect(describeControlChart(toControlChartSeries(CONTROL_CHART_ROWS))).toBe(
      '4 of 6 subgroups fall outside the control limits (2 below the lower limit, 2 above the upper limit); the subgroup mean runs above the grand mean from batch SIM0001-CNC-03-02-B04 onward.',
    );
  });

  it('reports a stable window without a run clause', () => {
    const rows = [
      subgroupRow(1, 'B01', 20.04),
      subgroupRow(2, 'B02', 20.05),
      subgroupRow(3, 'B03', 20.04),
      subgroupRow(4, 'B04', 20.05),
    ];
    expect(describeControlChart(toControlChartSeries(rows))).toBe(
      'All 4 subgroups fall inside the control limits.',
    );
    expect(describeControlChart(toControlChartSeries(rows.slice(0, 1)))).toBe(
      'All 1 subgroup fall inside the control limits.',
    );
  });

  it('explains missing control limits and an empty window', () => {
    expect(
      describeControlChart(toControlChartSeries(controlChartRows({ ucl: null, lcl: null }))),
    ).toBe(
      'Control limits are not available because every subgroup in the window has a single sample.',
    );
    expect(describeControlChart(toControlChartSeries([]))).toBe(
      'No subgroups fall inside the selected window.',
    );
  });
});

describe('sharedBatchPrefix', () => {
  it('returns the shared hyphen-delimited prefix, or nothing when there is no shared segment', () => {
    expect(sharedBatchPrefix(['SIM0001-CNC-03-01-B01', 'SIM0001-CNC-03-02-B04'])).toBe(
      'SIM0001-CNC-03-',
    );
    expect(sharedBatchPrefix(['SIM0001-CNC-03-01-B01', 'SIM0010-CNC-03-01-B01'])).toBe('');
    expect(sharedBatchPrefix(['SIM0001-CNC-03-01-B01'])).toBe('');
    expect(sharedBatchPrefix([])).toBe('');
  });
});
