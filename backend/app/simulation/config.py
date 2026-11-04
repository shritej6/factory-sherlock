"""Simulation inputs.

The engine is a pure function of ``SimulationConfig`` plus the reference data
it is handed, so the same seed always yields the same factory history.
"""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.models.enums import MachineStatus


class FaultKind(enum.StrEnum):
    TOOL_WEAR = "TOOL_WEAR"
    CALIBRATION_DRIFT = "CALIBRATION_DRIFT"
    VARIATION = "VARIATION"
    MATERIAL_ISSUE = "MATERIAL_ISSUE"
    DOWNTIME = "DOWNTIME"


@dataclass(frozen=True)
class FaultScenario:
    machine_code: str
    kind: FaultKind
    start_batch_index: int


@dataclass(frozen=True)
class SimulationConfig:
    seed: int
    start_time: datetime
    batches_per_machine: int = 12
    units_per_batch: int = 20
    minutes_per_batch: int = 30
    batches_per_order: int = 4
    faults: tuple[FaultScenario, ...] = ()
    # A batch whose failed/inspected ratio reaches this value raises an alert.
    alert_defect_rate: float = 0.15

    def __post_init__(self) -> None:
        if self.batches_per_machine < 1 or self.units_per_batch < 1:
            raise ValueError("batches_per_machine and units_per_batch must be at least 1")
        if self.minutes_per_batch < 1 or self.batches_per_order < 1:
            raise ValueError("minutes_per_batch and batches_per_order must be at least 1")


@dataclass(frozen=True)
class SpecRef:
    specification_id: int
    characteristic: str
    target: Decimal
    tolerance: Decimal


@dataclass(frozen=True)
class ProductRef:
    product_id: int
    code: str
    specs: tuple[SpecRef, ...]
    # Material lot ids usable for this product, in rotation order.
    material_lot_ids: tuple[int, ...]


@dataclass(frozen=True)
class MachineRef:
    machine_id: int
    code: str
    status: MachineStatus = MachineStatus.IDLE


@dataclass(frozen=True)
class Catalog:
    """Reference rows the simulator needs; loaded by the service from MySQL."""

    products: tuple[ProductRef, ...]
    machines: tuple[MachineRef, ...]
    defect_type_ids: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.products or not self.machines:
            raise ValueError("catalog needs at least one product and one machine")
        for product in self.products:
            if not product.specs or not product.material_lot_ids:
                raise ValueError(f"product {product.code} needs specifications and material lots")
