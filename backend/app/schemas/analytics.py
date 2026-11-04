from typing import Any

from pydantic import BaseModel


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
