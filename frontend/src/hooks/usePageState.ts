import { useCallback, useState } from 'react';

import { DEFAULT_PAGE_SIZE } from '@/types/constants';

export interface PageState {
  limit: number;
  offset: number;
}

/**
 * Holds the limit and offset for one paged list. Screens call resetOffset whenever a
 * filter changes so the user is not left on a page that no longer exists.
 */
export function usePageState(initialLimit = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState<PageState>({ limit: initialLimit, offset: 0 });
  const resetOffset = useCallback(
    () => setPage((current) => (current.offset === 0 ? current : { ...current, offset: 0 })),
    [],
  );
  return { page, setPage, resetOffset };
}
