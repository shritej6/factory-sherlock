import type { QueryClient } from '@tanstack/react-query';

/**
 * Root query keys touched by any production-side mutation. Machine status,
 * order, batch, inspection, and lot changes all move downstream figures
 * (summaries, analytics, alerts, traces), so every such mutation refreshes the set.
 * `trace` is the root of the forward and backward trace keys on the Traceability
 * screen, whose lot and batch statuses change when a lot is quarantined.
 */
const PRODUCTION_KEYS = [
  'batches',
  'orders',
  'units',
  'inspections',
  'quality-summary',
  'analytics',
  'alerts',
  'machines',
  'material-lots',
  'investigations',
  'trace',
] as const;

export function invalidateProduction(queryClient: QueryClient): void {
  for (const key of PRODUCTION_KEYS) {
    void queryClient.invalidateQueries({ queryKey: [key] });
  }
}
