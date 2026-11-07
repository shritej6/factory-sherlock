import { describe, expect, it } from 'vitest';

import { formatMeasure, formatPercent } from './format';

describe('formatMeasure', () => {
  it('shows three decimals for numbers and numeric strings', () => {
    expect(formatMeasure(12.5)).toBe('12.500');
    expect(formatMeasure('0.1')).toBe('0.100');
  });

  it('reads as n/a when there is no value', () => {
    expect(formatMeasure(null)).toBe('n/a');
    expect(formatMeasure(undefined)).toBe('n/a');
  });

  it('passes non-numeric text through unchanged', () => {
    expect(formatMeasure('pending')).toBe('pending');
  });
});

describe('formatPercent', () => {
  it('turns a fraction into a percentage with the requested precision', () => {
    expect(formatPercent(0.0958)).toBe('9.6%');
    expect(formatPercent(0.05, 0)).toBe('5%');
  });
});
