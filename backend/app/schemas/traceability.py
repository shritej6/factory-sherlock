from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import BatchStatus, MaterialLotStatus
from app.schemas.catalog import MaterialLotRead
from app.schemas.production import ProductionBatchRead


class ForwardTraceRow(BaseModel):
    """One batch reached by a material lot (query 04)."""

    lot_number: str
    material_name: str
    supplier: str
    lot_status: MaterialLotStatus
    batch_id: int
    batch_number: str
    batch_status: BatchStatus
    started_at: datetime
    machine_code: str
    order_number: str
    product_name: str
    quantity_used: Decimal
    units_produced: int
    units_failed: int


class ForwardTraceRead(BaseModel):
    lot_number: str
    batches: list[ForwardTraceRow]


class BackwardTraceRow(BaseModel):
    """One material lot in the lineage of a serial number (query 05)."""

    serial_number: str
    produced_at: datetime
    batch_number: str
    batch_status: BatchStatus
    machine_code: str
    machine_name: str
    order_number: str
    product_code: str
    product_name: str
    lot_number: str
    material_name: str
    supplier: str
    lot_status: MaterialLotStatus
    inspection_summary: str | None


class BackwardTraceRead(BaseModel):
    serial_number: str
    lineage: list[BackwardTraceRow]


class LotQuarantineRead(BaseModel):
    lot: MaterialLotRead
    quarantined_batches: list[ProductionBatchRead]
