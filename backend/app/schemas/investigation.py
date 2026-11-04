from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AlertType, InvestigationStatus, Severity
from app.schemas.common import ApiModel


class InvestigationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=150)
    machine_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(
        default=None,
        gt=0,
        description="Label shown on the case board; rules scope by machine and window only",
    )
    window_start: datetime
    window_end: datetime

    @model_validator(mode="after")
    def _window_is_ordered(self) -> "InvestigationCreate":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class InvestigationStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: InvestigationStatus
    conclusion: str | None = Field(default=None, max_length=4000)


class EvidenceRead(ApiModel):
    id: int
    sequence: int
    rule_code: str
    title: str
    narrative: str
    query_name: str
    query_sql: str
    result_rows: list[dict[str, Any]]

    @field_validator("result_rows", mode="before")
    @classmethod
    def _rows_from_payload(cls, value: object) -> object:
        """Rebuild ordered row dictionaries from the stored column and array form."""
        if isinstance(value, dict) and "columns" in value:
            columns = value["columns"]
            return [dict(zip(columns, row, strict=True)) for row in value["rows"]]
        return value


class InvestigationBatchRead(ApiModel):
    batch_id: int
    reason: str


class InvestigationRead(ApiModel):
    id: int
    title: str
    machine_id: int | None
    product_id: int | None
    window_start: datetime
    window_end: datetime
    status: InvestigationStatus
    summary: str | None
    conclusion: str | None
    created_at: datetime
    closed_at: datetime | None
    evidence: list[EvidenceRead]
    batch_links: list[InvestigationBatchRead]


class AlertRead(ApiModel):
    id: int
    machine_id: int | None
    alert_type: AlertType
    severity: Severity
    message: str
    created_at: datetime
    acknowledged_at: datetime | None
