from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation import AlertRead


class QueryCatalogEntry(BaseModel):
    """One documented SQL file as listed by the SQL explorer."""

    name: str
    description: str
    sql: str
    runnable: bool
    parameters: list[str]


class QueryResult(BaseModel):
    """Output of running a dashboard query: the SQL, the bound parameters, and the rows."""

    query: str
    sql: str
    params: dict[str, Any]
    rows: list[dict[str, Any]]


class OverdueCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: datetime | None = Field(
        default=None,
        description="Moment the due dates are judged against; defaults to the server clock",
    )


class OverdueCheckResponse(BaseModel):
    """Outcome of one overdue order check: how many orders were overdue and what was raised."""

    checked: int
    raised: int
    alerts: list[AlertRead]
