import { keepPreviousData, useQueries, useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';

import {
  analyticsApi,
  catalogApi,
  investigationApi,
  productionApi,
  qualityApi,
} from '@/services/api';
import type {
  BatchListParams,
  InspectionListParams,
  OrderListParams,
  OrderStatus,
  Page,
  PageParams,
  ProductionOrder,
  QueryParams,
} from '@/types/api';

/**
 * The largest page the API serves. Screens that use a list as a lookup (dropdowns,
 * id to code maps) request this page instead of paging through the table.
 */
export const LOOKUP_PAGE: PageParams = { limit: 500, offset: 0 };

/** Requests a single row so only the envelope's total is of interest. */
const COUNT_PAGE: PageParams = { limit: 1, offset: 0 };

export const queryKeys = {
  machines: ['machines'] as const,
  machineEvents: (id: number) => ['machines', id, 'events'] as const,
  machineEventPage: (id: number, page: PageParams) => ['machines', id, 'events', page] as const,
  products: ['products'] as const,
  specifications: ['specifications'] as const,
  materialLots: ['material-lots'] as const,
  defectTypes: ['defect-types'] as const,
  orders: (params: OrderListParams) => ['orders', params] as const,
  batches: (params: BatchListParams) => ['batches', params] as const,
  inspections: (params: InspectionListParams) => ['inspections', params] as const,
  qualitySummary: (filters: { machine_id?: number; batch_id?: number }) =>
    ['quality-summary', filters] as const,
  investigations: ['investigations'] as const,
  investigationPage: (page: PageParams) => ['investigations', 'list', page] as const,
  investigation: (id: number) => ['investigations', id] as const,
  alerts: ['alerts'] as const,
  alertPage: (page: PageParams) => ['alerts', page] as const,
  catalog: ['analytics', 'catalog'] as const,
  analytics: (name: string, params: QueryParams) => ['analytics', name, params] as const,
};

export const useMachines = () =>
  useQuery({ queryKey: queryKeys.machines, queryFn: catalogApi.machines });
export const useProducts = () =>
  useQuery({ queryKey: queryKeys.products, queryFn: catalogApi.products });
export const useSpecifications = () =>
  useQuery({ queryKey: queryKeys.specifications, queryFn: catalogApi.specifications });
export const useMaterialLots = () =>
  useQuery({ queryKey: queryKeys.materialLots, queryFn: catalogApi.materialLots });
export const useDefectTypes = () =>
  useQuery({ queryKey: queryKeys.defectTypes, queryFn: catalogApi.defectTypes });

export const useMachineEvents = (machineId: number | null, page: PageParams = {}) =>
  useQuery({
    queryKey: queryKeys.machineEventPage(machineId ?? 0, page),
    queryFn: () => catalogApi.machineEvents(machineId ?? 0, page),
    enabled: machineId !== null,
    placeholderData: keepPreviousData,
  });

export const useOrders = (params: OrderListParams = {}) =>
  useQuery({
    queryKey: queryKeys.orders(params),
    queryFn: () => productionApi.orders(params),
    placeholderData: keepPreviousData,
  });

export const useBatches = (params: BatchListParams = {}) =>
  useQuery({
    queryKey: queryKeys.batches(params),
    queryFn: () => productionApi.batches(params),
    placeholderData: keepPreviousData,
  });

export const useInspections = (params: InspectionListParams = {}) =>
  useQuery({
    queryKey: queryKeys.inspections(params),
    queryFn: () => qualityApi.inspections(params),
    placeholderData: keepPreviousData,
  });

export const useQualitySummary = (filters: { machine_id?: number; batch_id?: number } = {}) =>
  useQuery({
    queryKey: queryKeys.qualitySummary(filters),
    queryFn: () => qualityApi.summary(filters),
  });

export const useInvestigations = (page: PageParams = {}) =>
  useQuery({
    queryKey: queryKeys.investigationPage(page),
    queryFn: () => investigationApi.list(page),
    placeholderData: keepPreviousData,
  });

export const useInvestigation = (id: number) =>
  useQuery({ queryKey: queryKeys.investigation(id), queryFn: () => investigationApi.get(id) });

export const useAlerts = (page: PageParams = {}) =>
  useQuery({
    queryKey: queryKeys.alertPage(page),
    queryFn: () => analyticsApi.alerts(page),
    placeholderData: keepPreviousData,
  });

export const useQueryCatalog = () =>
  useQuery({ queryKey: queryKeys.catalog, queryFn: analyticsApi.catalog });

export const useAnalyticsQuery = (name: string, params: QueryParams, enabled = true) =>
  useQuery({
    queryKey: queryKeys.analytics(name, params),
    queryFn: () => analyticsApi.run(name, params),
    enabled,
  });

export interface OrderCountsResult<S extends OrderStatus> {
  data: Record<S, number> | undefined;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<unknown>;
}

function combineOrderCounts<S extends OrderStatus>(
  statuses: readonly S[],
  results: UseQueryResult<Page<ProductionOrder>>[],
): OrderCountsResult<S> {
  const counts = {} as Record<S, number>;
  let complete = true;
  statuses.forEach((status, index) => {
    const total = results[index]?.data?.total;
    if (total === undefined) complete = false;
    else counts[status] = total;
  });
  return {
    data: complete ? counts : undefined,
    isPending: results.some((result) => result.isPending),
    isError: results.some((result) => result.isError),
    error: results.find((result) => result.isError)?.error ?? null,
    refetch: () => Promise.all(results.map((result) => result.refetch())),
  };
}

/**
 * Counts orders per status from the envelope totals. The list is paged, so counting
 * rows on the client would only cover one page; one single-row request per status
 * gives exact figures for any number of orders.
 */
export const useOrderCounts = <S extends OrderStatus>(statuses: readonly S[]) =>
  useQueries({
    queries: statuses.map((status) => ({
      queryKey: queryKeys.orders({ status, ...COUNT_PAGE }),
      queryFn: () => productionApi.orders({ status, ...COUNT_PAGE }),
    })),
    combine: (results) => combineOrderCounts(statuses, results),
  });
