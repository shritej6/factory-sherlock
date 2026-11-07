from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InspectionResult
from app.schemas.catalog import CODE_PATTERN
from app.schemas.common import ApiModel


class InspectionCreate(BaseModel):
    """Manual inspection entry. The result is computed server-side from the spec."""

    model_config = ConfigDict(extra="forbid")

    unit_id: int = Field(gt=0)
    specification_id: int = Field(gt=0)
    measured_value: Decimal = Field(decimal_places=3)
    inspected_at: datetime | None = None
    defect_type_codes: list[str] = Field(
        default_factory=list, max_length=10, json_schema_extra={"items": {"pattern": CODE_PATTERN}}
    )


class InspectionRead(ApiModel):
    id: int
    unit_id: int
    specification_id: int
    measured_value: Decimal
    result: InspectionResult
    inspected_at: datetime
    defect_codes: list[str] = Field(default_factory=list)


class QualitySummary(BaseModel):
    total_produced: int
    total_inspected: int
    passed: int
    failed: int
    defect_rate: float = Field(description="failed / total_inspected, 0 when nothing inspected")


class InspectionImportResult(BaseModel):
    """Outcome of a CSV import. The whole file was recorded or nothing was."""

    imported: int
    failed_inspections: int
    inspection_ids: list[int]
