import {
  keepPreviousData,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

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
  InvestigationListParams,
  OrderListParams,
  PageParams,
  QueryParams,
} from '@/types/api';
import { OPEN_INVESTIGATION_STATUSES, PRODUCIBLE_ORDER_STATUSES } from '@/types/constants';

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
  orderStatusCounts: ['orders', 'status-counts'] as const,
  batches: (params: BatchListParams) => ['batches', params] as const,
  inspections: (params: InspectionListParams) => ['inspections', params] as const,
  qualitySummary: (filters: { machine_id?: number; batch_id?: number }) =>
    ['quality-summary', filters] as const,
  investigations: ['investigations'] as const,
  investigationPage: (params: InvestigationListParams) =>
    ['investigations', 'list', params] as const,
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

/**
 * Orders that can start a batch. The order list filters by one status per request,
 * so each producible status is fetched with its own filter and the pages are joined;
 * the server does the filtering and the 500-row page only has to hold eligible orders.
 */
export const useProducibleOrders = () =>
  useQueries({
    queries: PRODUCIBLE_ORDER_STATUSES.map((status) => {
      const params: OrderListParams = { status, ...LOOKUP_PAGE };
      return { queryKey: queryKeys.orders(params), queryFn: () => productionApi.orders(params) };
    }),
    combine: (results) => ({
      data: results.every((result) => result.data)
        ? results.flatMap((result) => result.data?.items ?? [])
        : undefined,
      error: results.find((result) => result.isError)?.error ?? null,
      refetch: () => Promise.all(results.map((result) => result.refetch())),
    }),
  });

/** One GROUP BY on the server instead of one single-row list request per status. */
export const useOrderStatusCounts = () =>
  useQuery({ queryKey: queryKeys.orderStatusCounts, queryFn: productionApi.orderStatusCounts });

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

export const useInvestigations = (params: InvestigationListParams = {}) =>
  useQuery({
    queryKey: queryKeys.investigationPage(params),
    queryFn: () => investigationApi.list(params),
    placeholderData: keepPreviousData,
  });

/** Counts OPEN and IN_REVIEW cases from the envelope total of a one-row, status-filtered page. */
export const useOpenInvestigationCount = () => {
  const params: InvestigationListParams = { status: OPEN_INVESTIGATION_STATUSES, ...COUNT_PAGE };
  return useQuery({
    queryKey: queryKeys.investigationPage(params),
    queryFn: () => investigationApi.list(params),
    select: (page) => page.total,
  });
};

export const useInvestigation = (id: number) =>
  useQuery({ queryKey: queryKeys.investigation(id), queryFn: () => investigationApi.get(id) });

export const useAlerts = (page: PageParams = {}) =>
  useQuery({
    queryKey: queryKeys.alertPage(page),
    queryFn: () => analyticsApi.alerts(page),
    placeholderData: keepPreviousData,
  });

/**
 * Runs the overdue order check. Every alert page shares the `alerts` root key, so
 * invalidating it refreshes whichever page the Overview is showing.
 */
export const useCheckOverdueOrders = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: analyticsApi.checkOverdueOrders,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
  });
};

export const useQueryCatalog = () =>
  useQuery({ queryKey: queryKeys.catalog, queryFn: analyticsApi.catalog });

export const useAnalyticsQuery = (name: string, params: QueryParams, enabled = true) =>
  useQuery({
    queryKey: queryKeys.analytics(name, params),
    queryFn: () => analyticsApi.run(name, params),
    enabled,
  });
