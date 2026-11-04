import { useQuery } from '@tanstack/react-query';

import {
  analyticsApi,
  catalogApi,
  investigationApi,
  productionApi,
  qualityApi,
} from '@/services/api';
import type { InspectionResult, OrderStatus, QueryParams } from '@/types/api';

export const queryKeys = {
  machines: ['machines'] as const,
  machineEvents: (id: number) => ['machines', id, 'events'] as const,
  products: ['products'] as const,
  materialLots: ['material-lots'] as const,
  defectTypes: ['defect-types'] as const,
  orders: (status?: OrderStatus | '') => ['orders', status ?? ''] as const,
  batches: (filters: { order_id?: number; machine_id?: number }) => ['batches', filters] as const,
  inspections: (filters: { batch_id?: number; result?: InspectionResult | '' }) =>
    ['inspections', filters] as const,
  qualitySummary: (filters: { machine_id?: number; batch_id?: number }) =>
    ['quality-summary', filters] as const,
  investigations: ['investigations'] as const,
  investigation: (id: number) => ['investigations', id] as const,
  alerts: ['alerts'] as const,
  catalog: ['analytics', 'catalog'] as const,
  analytics: (name: string, params: QueryParams) => ['analytics', name, params] as const,
};

export const useMachines = () =>
  useQuery({ queryKey: queryKeys.machines, queryFn: catalogApi.machines });
export const useProducts = () =>
  useQuery({ queryKey: queryKeys.products, queryFn: catalogApi.products });
export const useMaterialLots = () =>
  useQuery({ queryKey: queryKeys.materialLots, queryFn: catalogApi.materialLots });
export const useDefectTypes = () =>
  useQuery({ queryKey: queryKeys.defectTypes, queryFn: catalogApi.defectTypes });

export const useMachineEvents = (machineId: number | null) =>
  useQuery({
    queryKey: queryKeys.machineEvents(machineId ?? 0),
    queryFn: () => catalogApi.machineEvents(machineId ?? 0),
    enabled: machineId !== null,
  });

export const useOrders = (status?: OrderStatus | '') =>
  useQuery({ queryKey: queryKeys.orders(status), queryFn: () => productionApi.orders(status) });

export const useBatches = (filters: { order_id?: number; machine_id?: number } = {}) =>
  useQuery({ queryKey: queryKeys.batches(filters), queryFn: () => productionApi.batches(filters) });

export const useInspections = (filters: { batch_id?: number; result?: InspectionResult | '' }) =>
  useQuery({
    queryKey: queryKeys.inspections(filters),
    queryFn: () => qualityApi.inspections({ ...filters, limit: 500 }),
  });

export const useQualitySummary = (filters: { machine_id?: number; batch_id?: number } = {}) =>
  useQuery({
    queryKey: queryKeys.qualitySummary(filters),
    queryFn: () => qualityApi.summary(filters),
  });

export const useInvestigations = () =>
  useQuery({ queryKey: queryKeys.investigations, queryFn: investigationApi.list });

export const useInvestigation = (id: number) =>
  useQuery({ queryKey: queryKeys.investigation(id), queryFn: () => investigationApi.get(id) });

export const useAlerts = () =>
  useQuery({ queryKey: queryKeys.alerts, queryFn: () => analyticsApi.alerts(20) });

export const useQueryCatalog = () =>
  useQuery({ queryKey: queryKeys.catalog, queryFn: analyticsApi.catalog });

export const useAnalyticsQuery = (name: string, params: QueryParams, enabled = true) =>
  useQuery({
    queryKey: queryKeys.analytics(name, params),
    queryFn: () => analyticsApi.run(name, params),
    enabled,
  });
