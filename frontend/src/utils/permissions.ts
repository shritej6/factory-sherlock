import type { UserRole } from '@/types/api';

/**
 * Mirrors the role guards on the backend routes. Viewers are read-only,
 * operators get every operator capability, engineers and admins get everything.
 */
export type Capability =
  | 'machine.changeStatus'
  | 'order.create'
  | 'order.edit'
  | 'order.transition'
  | 'batch.create'
  | 'batch.complete'
  | 'batch.quarantine'
  | 'inspection.record'
  | 'investigation.manage'
  | 'lot.quarantine'
  | 'simulation.run'
  | 'alert.acknowledge';

const OPERATOR_CAPABILITIES: readonly Capability[] = [
  'machine.changeStatus',
  'order.transition',
  'batch.create',
  'batch.complete',
  'inspection.record',
  'alert.acknowledge',
];

const ENGINEER_CAPABILITIES: readonly Capability[] = [
  ...OPERATOR_CAPABILITIES,
  'order.create',
  'order.edit',
  'batch.quarantine',
  'investigation.manage',
  'lot.quarantine',
  'simulation.run',
];

const ROLE_CAPABILITIES: Record<UserRole, readonly Capability[]> = {
  ADMIN: ENGINEER_CAPABILITIES,
  ENGINEER: ENGINEER_CAPABILITIES,
  OPERATOR: OPERATOR_CAPABILITIES,
  VIEWER: [],
};

export function can(role: UserRole | null | undefined, capability: Capability): boolean {
  if (!role) return false;
  return ROLE_CAPABILITIES[role].includes(capability);
}
