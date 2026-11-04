"""Executes named SQL files with bound parameters and returns JSON-friendly rows."""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.repositories.sql_loader import load_query, load_sql

EXPANDING_PARAMS: dict[str, tuple[str, ...]] = {
    "investigation.shared_material_lots": ("batch_ids",),
}


class QueryRunner(Protocol):
    """Interface the investigation rules depend on (so tests can fake it)."""

    def run(self, name: str, params: Mapping[str, Any]) -> list[dict[str, Any]]: ...

    def sql(self, name: str) -> str: ...


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        # SUM over integer columns comes back as Decimal('47'); keep counts as ints.
        exponent = value.as_tuple().exponent
        return int(value) if isinstance(exponent, int) and exponent >= 0 else float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class SqlQueryRunner:
    def __init__(self, session: Session) -> None:
        self._session = session

    def run(self, name: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        clause = load_query(name, expanding=EXPANDING_PARAMS.get(name, ()))
        result = self._session.execute(clause, dict(params))
        return [{k: _jsonable(v) for k, v in row.items()} for row in result.mappings().all()]

    def sql(self, name: str) -> str:
        return load_sql(name)
