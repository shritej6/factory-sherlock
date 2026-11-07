from datetime import date, datetime
from decimal import Decimal

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.models.enums import BatchStatus, OrderStatus
from app.schemas.common import ApiModel


class ProductionOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_number: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,29}$")
    product_id: int = Field(gt=0)
    machine_id: int | None = Field(default=None, gt=0)
    quantity_planned: int = Field(gt=0, le=100_000)
    due_date: date | None = None


class ProductionOrderUpdate(BaseModel):
    """Only fields that are safe to change before production starts."""

    model_config = ConfigDict(extra="forbid")

    machine_id: int | None = Field(default=None, gt=0)
    quantity_planned: int | None = Field(default=None, gt=0, le=100_000)
    due_date: date | None = None


class ProductionOrderStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus


class ProductionOrderRead(ApiModel):
    id: int
    order_number: str
    product_id: int
    machine_id: int | None
    quantity_planned: int
    quantity_completed: int
    status: OrderStatus
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class OrderStatusCounts(BaseModel):
    """Number of production orders in each status; one key per ``OrderStatus`` value."""

    PLANNED: int
    RELEASED: int
    IN_PROGRESS: int
    COMPLETED: int
    CANCELLED: int


class BatchMaterialInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_lot_id: int = Field(gt=0)
    quantity_used: Decimal = Field(gt=0, decimal_places=2)


class BatchMaterialRead(ApiModel):
    material_lot_id: int
    quantity_used: Decimal


class ProductionBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    production_order_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=10_000)
    materials: list[BatchMaterialInput] = Field(min_length=1, max_length=50)


class ProductionBatchRead(ApiModel):
    id: int
    batch_number: str
    production_order_id: int
    order_number: str = Field(validation_alias=AliasPath("order", "order_number"))
    machine_id: int
    quantity: int
    status: BatchStatus
    started_at: datetime
    completed_at: datetime | None
    quarantine_reason: str | None
    material_links: list[BatchMaterialRead]


class QuarantineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=5, max_length=255)
