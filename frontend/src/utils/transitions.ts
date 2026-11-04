import type { BatchStatus, InvestigationStatus, MachineStatus, OrderStatus } from '@/types/api';

/** Transition tables copied from backend/app/domain/state_machines.py. */
export const ORDER_TRANSITIONS: Record<OrderStatus, readonly OrderStatus[]> = {
  PLANNED: ['RELEASED', 'CANCELLED'],
  RELEASED: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
};

export const MACHINE_TRANSITIONS: Record<MachineStatus, readonly MachineStatus[]> = {
  IDLE: ['RUNNING', 'STOPPED'],
  RUNNING: ['WARNING', 'STOPPED', 'FAULT', 'IDLE'],
  WARNING: ['RUNNING', 'STOPPED', 'FAULT'],
  FAULT: ['STOPPED'],
  STOPPED: ['IDLE'],
};

export const BATCH_TRANSITIONS: Record<BatchStatus, readonly BatchStatus[]> = {
  IN_PROGRESS: ['COMPLETED', 'QUARANTINED'],
  COMPLETED: ['QUARANTINED'],
  QUARANTINED: [],
};

export const INVESTIGATION_TRANSITIONS: Record<
  InvestigationStatus,
  readonly InvestigationStatus[]
> = {
  OPEN: ['IN_REVIEW', 'CLOSED'],
  IN_REVIEW: ['CLOSED', 'OPEN'],
  CLOSED: [],
};

export const EDITABLE_ORDER_STATES: readonly OrderStatus[] = ['PLANNED', 'RELEASED'];

export function legalOrderMoves(status: OrderStatus): readonly OrderStatus[] {
  return ORDER_TRANSITIONS[status] ?? [];
}

export function legalMachineMoves(status: MachineStatus): readonly MachineStatus[] {
  return MACHINE_TRANSITIONS[status] ?? [];
}

export function legalBatchMoves(status: BatchStatus): readonly BatchStatus[] {
  return BATCH_TRANSITIONS[status] ?? [];
}

export function legalInvestigationMoves(
  status: InvestigationStatus,
): readonly InvestigationStatus[] {
  return INVESTIGATION_TRANSITIONS[status] ?? [];
}

export function isOrderEditable(status: OrderStatus): boolean {
  return EDITABLE_ORDER_STATES.includes(status);
}
