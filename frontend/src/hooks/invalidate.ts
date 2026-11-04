import type { QueryClient } from '@tanstack/react-query';

/**
 * Root query keys touched by any production-side mutation. Machine status,
 * order, batch, inspection, and lot changes all move downstream figures
 * (summaries, analytics, alerts), so every such mutation refreshes the set.
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
] as const;

export function invalidateProduction(queryClient: QueryClient): void {
  for (const key of PRODUCTION_KEYS) {
    void queryClient.invalidateQueries({ queryKey: [key] });
  }
}
