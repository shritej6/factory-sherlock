"""Plain data produced by the simulation engine.

The engine never touches SQLAlchemy; the simulation service maps these
records onto ORM rows inside one transaction.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.models.enums import AlertType, InspectionResult, MachineEventType, MachineStatus, Severity


@dataclass(frozen=True)
class StateChange:
    machine_id: int
    previous: MachineStatus
    new: MachineStatus
    at: datetime
    reason: str


@dataclass(frozen=True)
class FaultEvent:
    machine_id: int
    event_type: MachineEventType
    severity: Severity
    description: str
    at: datetime


@dataclass(frozen=True)
class SimulatedInspection:
    specification_id: int
    measured_value: Decimal
    result: InspectionResult
    defect_codes: tuple[str, ...]
    at: datetime


@dataclass(frozen=True)
class SimulatedUnit:
    sequence_in_batch: int
    produced_at: datetime
    inspections: tuple[SimulatedInspection, ...]


@dataclass(frozen=True)
class SimulatedBatch:
    machine_id: int
    order_index: int
    batch_index: int
    material_lot_ids: tuple[int, ...]
    started_at: datetime
    completed_at: datetime
    units: tuple[SimulatedUnit, ...]

    @property
    def inspected(self) -> int:
        return sum(len(u.inspections) for u in self.units)

    @property
    def failed(self) -> int:
        return sum(
            1 for u in self.units for i in u.inspections if i.result is InspectionResult.FAIL
        )


@dataclass(frozen=True)
class SimulatedOrder:
    order_index: int
    machine_id: int
    product_id: int
    quantity_planned: int
    created_at: datetime
    due_date: datetime


@dataclass(frozen=True)
class SimulatedAlert:
    machine_id: int
    alert_type: AlertType
    severity: Severity
    message: str
    at: datetime


@dataclass
class SimulationOutput:
    seed: int
    orders: list[SimulatedOrder] = field(default_factory=list)
    batches: list[SimulatedBatch] = field(default_factory=list)
    state_changes: list[StateChange] = field(default_factory=list)
    fault_events: list[FaultEvent] = field(default_factory=list)
    alerts: list[SimulatedAlert] = field(default_factory=list)
    final_states: dict[int, MachineStatus] = field(default_factory=dict)
