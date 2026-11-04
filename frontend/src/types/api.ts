export type UserRole = 'ADMIN' | 'ENGINEER' | 'OPERATOR' | 'VIEWER';
export type MachineStatus = 'IDLE' | 'RUNNING' | 'WARNING' | 'STOPPED' | 'FAULT';
export type MachineEventType =
  | 'STATE_CHANGE'
  | 'TOOL_WEAR'
  | 'CALIBRATION_DRIFT'
  | 'MATERIAL_ISSUE'
  | 'DOWNTIME'
  | 'MAINTENANCE';
export type Severity = 'INFO' | 'WARNING' | 'CRITICAL';
export type OrderStatus = 'PLANNED' | 'RELEASED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type BatchStatus = 'IN_PROGRESS' | 'COMPLETED' | 'QUARANTINED';
export type MaterialLotStatus = 'AVAILABLE' | 'QUARANTINED' | 'CONSUMED';
export type InspectionResult = 'PASS' | 'FAIL';
export type AlertType =
  'HIGH_DEFECT_RATE' | 'MACHINE_FAULT' | 'MATERIAL_QUARANTINE' | 'ORDER_OVERDUE';
export type InvestigationStatus = 'OPEN' | 'IN_REVIEW' | 'CLOSED';
export type FaultKind =
  'TOOL_WEAR' | 'CALIBRATION_DRIFT' | 'VARIATION' | 'MATERIAL_ISSUE' | 'DOWNTIME';

export interface ErrorResponse {
  error: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface Specification {
  id: number;
  characteristic: string;
  target_value: string;
  tolerance: string;
  unit: string;
}

export interface Product {
  id: number;
  code: string;
  name: string;
  description: string | null;
  specifications: Specification[];
  created_at: string;
}

export interface Machine {
  id: number;
  code: string;
  name: string;
  status: MachineStatus;
  updated_at: string;
}

export interface MachineStatusChange {
  status: MachineStatus;
  reason: string;
}

export interface MachineEvent {
  id: number;
  machine_id: number;
  event_type: MachineEventType;
  previous_state: MachineStatus | null;
  new_state: MachineStatus | null;
  severity: Severity;
  description: string;
  occurred_at: string;
}

export interface DefectType {
  id: number;
  code: string;
  name: string;
  description: string | null;
}

export interface MaterialLot {
  id: number;
  lot_number: string;
  material_name: string;
  supplier: string;
  quantity_received: string;
  status: MaterialLotStatus;
  received_at: string;
}

export interface ProductionOrder {
  id: number;
  order_number: string;
  product_id: number;
  machine_id: number | null;
  quantity_planned: number;
  quantity_completed: number;
  status: OrderStatus;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductionOrderCreate {
  order_number: string;
  product_id: number;
  machine_id?: number | null;
  quantity_planned: number;
  due_date?: string | null;
}

export interface ProductionOrderUpdate {
  machine_id?: number | null;
  quantity_planned?: number;
  due_date?: string | null;
}

export interface BatchMaterialInput {
  material_lot_id: number;
  quantity_used: string;
}

export interface BatchMaterial {
  material_lot_id: number;
  quantity_used: string;
}

export interface ProductionBatchCreate {
  production_order_id: number;
  quantity: number;
  materials: BatchMaterialInput[];
}

export interface ProductionBatch {
  id: number;
  batch_number: string;
  production_order_id: number;
  machine_id: number;
  quantity: number;
  status: BatchStatus;
  started_at: string;
  completed_at: string | null;
  quarantine_reason: string | null;
  material_links: BatchMaterial[];
}

export interface QuarantineRequest {
  reason: string;
}

export interface InspectionCreate {
  unit_id: number;
  specification_id: number;
  measured_value: string;
  inspected_at?: string | null;
  defect_type_codes?: string[];
}

export interface Inspection {
  id: number;
  unit_id: number;
  specification_id: number;
  measured_value: string;
  result: InspectionResult;
  inspected_at: string;
  defect_codes: string[];
}

export interface QualitySummary {
  total_produced: number;
  total_inspected: number;
  passed: number;
  failed: number;
  defect_rate: number;
}

export interface InvestigationCreate {
  title: string;
  machine_id?: number | null;
  product_id?: number | null;
  window_start: string;
  window_end: string;
}

export interface InvestigationStatusChange {
  status: InvestigationStatus;
  conclusion?: string | null;
}

export type ResultRow = Record<string, string | number | boolean | null>;

export interface Evidence {
  id: number;
  sequence: number;
  rule_code: string;
  title: string;
  narrative: string;
  query_name: string;
  query_sql: string;
  result_rows: ResultRow[];
}

export interface InvestigationBatchLink {
  batch_id: number;
  reason: string;
}

export interface Investigation {
  id: number;
  title: string;
  machine_id: number | null;
  product_id: number | null;
  window_start: string;
  window_end: string;
  status: InvestigationStatus;
  summary: string | null;
  conclusion: string | null;
  created_at: string;
  closed_at: string | null;
  evidence: Evidence[];
  batch_links: InvestigationBatchLink[];
}

export interface Alert {
  id: number;
  machine_id: number | null;
  alert_type: AlertType;
  severity: Severity;
  message: string;
  created_at: string;
  acknowledged_at: string | null;
}

export interface ForwardTraceRow extends ResultRow {
  lot_number: string;
  material_name: string;
  supplier: string;
  lot_status: MaterialLotStatus;
  batch_id: number;
  batch_number: string;
  batch_status: BatchStatus;
  started_at: string;
  machine_code: string;
  order_number: string;
  product_name: string;
  quantity_used: number;
  units_produced: number;
  units_failed: number;
}

export interface ForwardTrace {
  lot_number: string;
  batches: ForwardTraceRow[];
}

export interface BackwardTraceRow extends ResultRow {
  serial_number: string;
  produced_at: string;
  batch_number: string;
  batch_status: BatchStatus;
  machine_code: string;
  machine_name: string;
  order_number: string;
  product_code: string;
  product_name: string;
  lot_number: string | null;
  material_name: string | null;
  supplier: string | null;
  lot_status: MaterialLotStatus | null;
  inspection_summary: string | null;
}

export interface BackwardTrace {
  serial_number: string;
  lineage: BackwardTraceRow[];
}

export interface LotQuarantineResult {
  lot: MaterialLot;
  quarantined_batches: ProductionBatch[];
}

export interface QueryCatalogEntry {
  name: string;
  description: string;
  sql: string;
  /** True when the query accepts the generic dashboard parameters and can be executed here. */
  runnable: boolean;
  /** Names of the parameters the run endpoint binds for this query. */
  parameters: string[];
}

export interface QueryParams {
  window_start?: string;
  window_end?: string;
  machine_id?: number;
  threshold?: number;
  hours?: number;
  limit?: number;
}

export interface QueryResult {
  query: string;
  sql: string;
  params: Record<string, string | number | null>;
  rows: ResultRow[];
}

export interface FaultScenario {
  machine_code: string;
  fault: FaultKind;
  start_batch_index: number;
}

export interface SimulationRequest {
  seed: number;
  start_time: string;
  batches_per_machine: number;
  units_per_batch: number;
  minutes_per_batch: number;
  faults: FaultScenario[];
}

export interface SimulationResult {
  seed: number;
  orders_created: number;
  batches_created: number;
  units_created: number;
  inspections_created: number;
  failed_inspections: number;
  events_created: number;
  alerts_created: number;
}
