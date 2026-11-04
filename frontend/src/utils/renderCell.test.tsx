import { describe, expect, it } from 'vitest';

import { renderCell } from './renderCell';

describe('renderCell', () => {
  it('formats rate-like fractions as percentages and leaves counts alone', () => {
    expect(renderCell(0.978, 'share_of_machine_defects')).toBe('97.8%');
    expect(renderCell(0.0583, 'rate_change')).toBe('5.8%');
    expect(renderCell(75, 'completion_pct')).toBe('75');
    expect(renderCell(1400, 'inspected')).toBe('1,400');
  });

  it('normalises datetimes with either separator and labels nulls', () => {
    expect(renderCell('2026-11-02T11:30:00', 'started_at')).toBe('2026-11-02 11:30');
    expect(renderCell('2026-11-02 06:00:00', 'bucket_start')).toBe('2026-11-02 06:00');
    expect(renderCell(true, 'flag')).toBe('true');
  });
});
