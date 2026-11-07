import type {
  BatchStatus,
  FaultKind,
  InvestigationStatus,
  MachineStatus,
  OrderStatus,
  UserRole,
} from './api';

export const USER_ROLES: readonly UserRole[] = ['ADMIN', 'ENGINEER', 'OPERATOR', 'VIEWER'];
export const MACHINE_STATUSES: readonly MachineStatus[] = [
  'IDLE',
  'RUNNING',
  'WARNING',
  'STOPPED',
  'FAULT',
];
export const ORDER_STATUSES: readonly OrderStatus[] = [
  'PLANNED',
  'RELEASED',
  'IN_PROGRESS',
  'COMPLETED',
  'CANCELLED',
];
export const BATCH_STATUSES: readonly BatchStatus[] = ['IN_PROGRESS', 'COMPLETED', 'QUARANTINED'];
export const INVESTIGATION_STATUSES: readonly InvestigationStatus[] = [
  'OPEN',
  'IN_REVIEW',
  'CLOSED',
];
export const FAULT_KINDS: readonly FaultKind[] = [
  'TOOL_WEAR',
  'CALIBRATION_DRIFT',
  'VARIATION',
  'MATERIAL_ISSUE',
  'DOWNTIME',
];

/** Demo data is dated 2026-11-02 to 2026-11-03; these defaults bracket it. */
export const DEFAULT_WINDOW_START = '2026-11-01T00:00';
export const DEFAULT_WINDOW_END = '2026-11-05T00:00';

/** Page sizes offered by list screens; the API accepts 1 to 500 rows per page. */
export const PAGE_SIZES: readonly number[] = [25, 50, 100];
export const DEFAULT_PAGE_SIZE = 50;
