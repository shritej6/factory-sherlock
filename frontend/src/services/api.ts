import type {
  Alert,
  BackwardTrace,
  BatchListParams,
  DefectType,
  ForwardTrace,
  Inspection,
  InspectionCreate,
  InspectionImportResult,
  InspectionListParams,
  Investigation,
  InvestigationCreate,
  InvestigationStatusChange,
  LotQuarantineResult,
  LoginRequest,
  Machine,
  MachineEvent,
  MachineStatusChange,
  MaterialLot,
  OrderListParams,
  OrderStatus,
  Page,
  PageParams,
  Product,
  ProductionBatch,
  ProductionBatchCreate,
  ProductionOrder,
  ProductionOrderCreate,
  ProductionOrderUpdate,
  QualitySummary,
  QuarantineRequest,
  QueryCatalogEntry,
  QueryParams,
  QueryResult,
  SimulationRequest,
  SimulationResult,
  TokenResponse,
  User,
} from '@/types/api';

import { request } from './http';

export const authApi = {
  login: (body: LoginRequest) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body, auth: false }),
  me: () => request<User>('/auth/me'),
};

export const catalogApi = {
  products: () => request<Product[]>('/products'),
  machines: () => request<Machine[]>('/machines'),
  machine: (id: number) => request<Machine>(`/machines/${id}`),
  changeMachineStatus: (id: number, body: MachineStatusChange) =>
    request<Machine>(`/machines/${id}/status`, { method: 'POST', body }),
  machineEvents: (id: number, page: PageParams = {}) =>
    request<Page<MachineEvent>>(`/machines/${id}/events`, { query: page }),
  materialLots: () => request<MaterialLot[]>('/material-lots'),
  defectTypes: () => request<DefectType[]>('/defect-types'),
};

export const productionApi = {
  orders: (params: OrderListParams = {}) =>
    request<Page<ProductionOrder>>('/production-orders', { query: params }),
  createOrder: (body: ProductionOrderCreate) =>
    request<ProductionOrder>('/production-orders', { method: 'POST', body }),
  updateOrder: (id: number, body: ProductionOrderUpdate) =>
    request<ProductionOrder>(`/production-orders/${id}`, { method: 'PATCH', body }),
  changeOrderStatus: (id: number, status: OrderStatus) =>
    request<ProductionOrder>(`/production-orders/${id}/status`, {
      method: 'POST',
      body: { status },
    }),
  batches: (params: BatchListParams = {}) =>
    request<Page<ProductionBatch>>('/production-batches', { query: params }),
  createBatch: (body: ProductionBatchCreate) =>
    request<ProductionBatch>('/production-batches', { method: 'POST', body }),
  completeBatch: (id: number) =>
    request<ProductionBatch>(`/production-batches/${id}/complete`, { method: 'POST' }),
  quarantineBatch: (id: number, body: QuarantineRequest) =>
    request<ProductionBatch>(`/production-batches/${id}/quarantine`, { method: 'POST', body }),
};

export const qualityApi = {
  inspections: (params: InspectionListParams = {}) =>
    request<Page<Inspection>>('/inspections', { query: params }),
  recordInspection: (body: InspectionCreate) =>
    request<Inspection>('/inspections', { method: 'POST', body }),
  summary: (filters: { machine_id?: number; batch_id?: number } = {}) =>
    request<QualitySummary>('/quality/summary', { query: filters }),
  importInspections: (file: File) => {
    const body = new FormData();
    body.append('file', file);
    return request<InspectionImportResult>('/inspections/import', { method: 'POST', body });
  },
};

export const investigationApi = {
  list: (page: PageParams = {}) => request<Page<Investigation>>('/investigations', { query: page }),
  get: (id: number) => request<Investigation>(`/investigations/${id}`),
  open: (body: InvestigationCreate) =>
    request<Investigation>('/investigations', { method: 'POST', body }),
  changeStatus: (id: number, body: InvestigationStatusChange) =>
    request<Investigation>(`/investigations/${id}/status`, { method: 'POST', body }),
};

export const traceabilityApi = {
  forward: (lotNumber: string) =>
    request<ForwardTrace>(`/traceability/forward/${encodeURIComponent(lotNumber)}`),
  backward: (serialNumber: string) =>
    request<BackwardTrace>(`/traceability/backward/${encodeURIComponent(serialNumber)}`),
  quarantineLot: (lotId: number, body: QuarantineRequest) =>
    request<LotQuarantineResult>(`/traceability/material-lots/${lotId}/quarantine`, {
      method: 'POST',
      body,
    }),
};

export const analyticsApi = {
  catalog: () => request<QueryCatalogEntry[]>('/analytics/queries'),
  run: (name: string, params: QueryParams) =>
    request<QueryResult>(`/analytics/queries/${name}`, { query: { ...params } }),
  alerts: (page: PageParams = {}) => request<Page<Alert>>('/analytics/alerts', { query: page }),
  acknowledgeAlert: (id: number) =>
    request<Alert>(`/analytics/alerts/${id}/acknowledge`, { method: 'POST' }),
};

export const simulationApi = {
  run: (body: SimulationRequest) =>
    request<SimulationResult>('/simulation/runs', { method: 'POST', body }),
};
