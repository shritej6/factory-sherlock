import type {
  Alert,
  BackwardTrace,
  DefectType,
  ForwardTrace,
  Inspection,
  InspectionCreate,
  InspectionResult,
  Investigation,
  InvestigationCreate,
  InvestigationStatusChange,
  LotQuarantineResult,
  LoginRequest,
  Machine,
  MachineEvent,
  MachineStatusChange,
  MaterialLot,
  OrderStatus,
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
  machineEvents: (id: number, limit = 100) =>
    request<MachineEvent[]>(`/machines/${id}/events`, { query: { limit } }),
  materialLots: () => request<MaterialLot[]>('/material-lots'),
  defectTypes: () => request<DefectType[]>('/defect-types'),
};

export const productionApi = {
  orders: (status?: OrderStatus | '') =>
    request<ProductionOrder[]>('/production-orders', { query: { status } }),
  createOrder: (body: ProductionOrderCreate) =>
    request<ProductionOrder>('/production-orders', { method: 'POST', body }),
  updateOrder: (id: number, body: ProductionOrderUpdate) =>
    request<ProductionOrder>(`/production-orders/${id}`, { method: 'PATCH', body }),
  changeOrderStatus: (id: number, status: OrderStatus) =>
    request<ProductionOrder>(`/production-orders/${id}/status`, {
      method: 'POST',
      body: { status },
    }),
  batches: (filters: { order_id?: number; machine_id?: number } = {}) =>
    request<ProductionBatch[]>('/production-batches', { query: filters }),
  createBatch: (body: ProductionBatchCreate) =>
    request<ProductionBatch>('/production-batches', { method: 'POST', body }),
  completeBatch: (id: number) =>
    request<ProductionBatch>(`/production-batches/${id}/complete`, { method: 'POST' }),
  quarantineBatch: (id: number, body: QuarantineRequest) =>
    request<ProductionBatch>(`/production-batches/${id}/quarantine`, { method: 'POST', body }),
};

export const qualityApi = {
  inspections: (filters: { batch_id?: number; result?: InspectionResult | ''; limit?: number }) =>
    request<Inspection[]>('/inspections', { query: filters }),
  recordInspection: (body: InspectionCreate) =>
    request<Inspection>('/inspections', { method: 'POST', body }),
  summary: (filters: { machine_id?: number; batch_id?: number } = {}) =>
    request<QualitySummary>('/quality/summary', { query: filters }),
};

export const investigationApi = {
  list: () => request<Investigation[]>('/investigations'),
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
  alerts: (limit = 20) => request<Alert[]>('/analytics/alerts', { query: { limit } }),
  acknowledgeAlert: (id: number) =>
    request<Alert>(`/analytics/alerts/${id}/acknowledge`, { method: 'POST' }),
};

export const simulationApi = {
  run: (body: SimulationRequest) =>
    request<SimulationResult>('/simulation/runs', { method: 'POST', body }),
};
