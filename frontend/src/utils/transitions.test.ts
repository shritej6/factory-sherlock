import { describe, expect, it } from 'vitest';

import {
  isOrderEditable,
  legalBatchMoves,
  legalInvestigationMoves,
  legalMachineMoves,
  legalOrderMoves,
} from './transitions';

describe('legalOrderMoves', () => {
  it('matches the backend order state machine', () => {
    expect(legalOrderMoves('PLANNED')).toEqual(['RELEASED', 'CANCELLED']);
    expect(legalOrderMoves('RELEASED')).toEqual(['IN_PROGRESS', 'CANCELLED']);
    expect(legalOrderMoves('IN_PROGRESS')).toEqual(['COMPLETED', 'CANCELLED']);
    expect(legalOrderMoves('COMPLETED')).toEqual([]);
    expect(legalOrderMoves('CANCELLED')).toEqual([]);
  });

  it('never offers a move back to PLANNED', () => {
    for (const status of ['RELEASED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'] as const) {
      expect(legalOrderMoves(status)).not.toContain('PLANNED');
    }
  });
});

describe('other state machines', () => {
  it('only allows editing planned and released orders', () => {
    expect(isOrderEditable('PLANNED')).toBe(true);
    expect(isOrderEditable('RELEASED')).toBe(true);
    expect(isOrderEditable('IN_PROGRESS')).toBe(false);
  });

  it('requires a faulted machine to stop before running again', () => {
    expect(legalMachineMoves('FAULT')).toEqual(['STOPPED']);
    expect(legalMachineMoves('STOPPED')).toEqual(['IDLE']);
  });

  it('treats quarantined batches and closed investigations as terminal', () => {
    expect(legalBatchMoves('QUARANTINED')).toEqual([]);
    expect(legalBatchMoves('COMPLETED')).toEqual(['QUARANTINED']);
    expect(legalInvestigationMoves('CLOSED')).toEqual([]);
    expect(legalInvestigationMoves('IN_REVIEW')).toEqual(['CLOSED', 'OPEN']);
  });
});
