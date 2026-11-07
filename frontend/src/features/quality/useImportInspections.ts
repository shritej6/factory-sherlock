import { useMutation, useQueryClient } from '@tanstack/react-query';

import { invalidateProduction } from '@/hooks/invalidate';
import { qualityApi } from '@/services/api';

/**
 * Uploads a CSV of inspections. The import moves inspection lists, the quality
 * summary and every downstream figure, so the whole production key set is refreshed.
 */
export function useImportInspections() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => qualityApi.importInspections(file),
    onSuccess: () => invalidateProduction(queryClient),
  });
}
