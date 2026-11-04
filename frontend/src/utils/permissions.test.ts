import { describe, expect, it } from 'vitest';

import { can } from './permissions';

describe('can', () => {
  it('gives viewers read-only access, including no alert acknowledgement', () => {
    expect(can('VIEWER', 'alert.acknowledge')).toBe(false);
    expect(can('VIEWER', 'machine.changeStatus')).toBe(false);
    expect(can('VIEWER', 'investigation.manage')).toBe(false);
  });

  it('limits operators to shop-floor actions', () => {
    expect(can('OPERATOR', 'machine.changeStatus')).toBe(true);
    expect(can('OPERATOR', 'batch.create')).toBe(true);
    expect(can('OPERATOR', 'inspection.record')).toBe(true);
    expect(can('OPERATOR', 'alert.acknowledge')).toBe(true);
    expect(can('OPERATOR', 'order.create')).toBe(false);
    expect(can('OPERATOR', 'batch.quarantine')).toBe(false);
    expect(can('OPERATOR', 'simulation.run')).toBe(false);
  });

  it('gives engineers and admins everything, and nobody when signed out', () => {
    expect(can('ENGINEER', 'simulation.run')).toBe(true);
    expect(can('ADMIN', 'lot.quarantine')).toBe(true);
    expect(can(null, 'alert.acknowledge')).toBe(false);
  });
});
