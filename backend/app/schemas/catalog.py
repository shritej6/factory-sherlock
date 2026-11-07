"""Schemas for products, specifications, machines, defect types, and material lots."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MachineEventType, MachineStatus, MaterialLotStatus, Severity
from app.schemas.common import ApiModel

CODE_PATTERN = r"^[A-Z0-9][A-Z0-9_-]{1,29}$"


class SpecificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    characteristic: str = Field(min_length=1, max_length=50)
    target_value: Decimal = Field(gt=0, decimal_places=3)
    tolerance: Decimal = Field(gt=0, decimal_places=3)
    unit: str = Field(default="mm", max_length=10)


class SpecificationRead(ApiModel):
    id: int
    characteristic: str
    target_value: Decimal
    tolerance: Decimal
    unit: str


class SpecificationListItem(ApiModel):
    """One specification with its product code, for pickers such as the control chart."""

    id: int
    product_id: int
    product_code: str
    characteristic: str
    target_value: Decimal
    tolerance: Decimal
    unit: str


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=CODE_PATTERN)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    specifications: list[SpecificationCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ProductRead(ApiModel):
    id: int
    code: str
    name: str
    description: str | None
    specifications: list[SpecificationRead]
    created_at: datetime


class MachineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=CODE_PATTERN)
    name: str = Field(min_length=1, max_length=100)


class MachineRead(ApiModel):
    id: int
    code: str
    name: str
    status: MachineStatus
    updated_at: datetime


class MachineStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MachineStatus
    reason: str = Field(min_length=1, max_length=255)


class MachineEventRead(ApiModel):
    id: int
    machine_id: int
    event_type: MachineEventType
    previous_state: MachineStatus | None
    new_state: MachineStatus | None
    severity: Severity
    description: str
    occurred_at: datetime


class DefectTypeRead(ApiModel):
    id: int
    code: str
    name: str
    description: str | None


class MaterialLotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lot_number: str = Field(pattern=CODE_PATTERN)
    material_name: str = Field(min_length=1, max_length=100)
    supplier: str = Field(min_length=1, max_length=100)
    quantity_received: Decimal = Field(ge=0, decimal_places=2)
    received_at: datetime


class MaterialLotRead(ApiModel):
    id: int
    lot_number: str
    material_name: str
    supplier: str
    quantity_received: Decimal
    status: MaterialLotStatus
    received_at: datetime
