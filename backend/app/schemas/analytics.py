from typing import Any

from pydantic import BaseModel

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


class OverdueCheckResponse(BaseModel):
    """Outcome of one overdue order check: how many orders were overdue and what was raised."""

    checked: int
    raised: int
    alerts: list[AlertRead]
