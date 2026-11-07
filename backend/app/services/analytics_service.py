"""Thin wrapper that exposes the documented SQL queries to the API."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now
from app.core.exceptions import NotFoundError, ValidationError
from app.models import Alert
from app.repositories.query_runner import SqlQueryRunner
from app.repositories.sql_loader import load_sql, query_names

DASHBOARD_QUERIES = {
    "machine_defect_rate_comparison": ("window_start", "window_end"),
    "recurring_defects": ("window_start", "window_end", "machine_id"),
    "daily_production_trend": ("window_start", "window_end"),
    "order_completion_summary": (),
    "production_performance": ("limit",),
    "batches_requiring_review": ("window_start", "window_end", "threshold", "machine_id"),
    "quality_after_machine_events": ("machine_id", "window_start", "window_end", "hours"),
    "characteristic_control_chart": (
        "specification_id",
        "window_start",
        "window_end",
        "machine_id",
    ),
}


def run_dashboard_query(session: Session, name: str, params: dict[str, Any]) -> dict[str, Any]:
    if name not in query_names():
        raise NotFoundError(f"Query {name} does not exist")
    if name not in DASHBOARD_QUERIES:
        raise ValidationError(
            f"Query {name} needs entity-specific inputs and runs through its own screen",
            details={"runnable_queries": sorted(DASHBOARD_QUERIES)},
        )
    allowed = DASHBOARD_QUERIES[name]
    if "window_end" in allowed and params["window_end"] <= params["window_start"]:
        raise ValidationError("window_end must be after window_start")
    if "specification_id" in allowed and params.get("specification_id") is None:
        raise ValidationError("specification_id is required for this query")
    bound = {k: params.get(k) for k in allowed}
    rows = SqlQueryRunner(session).run(name, bound)
    return {"query": name, "sql": load_sql(name), "params": _jsonable(bound), "rows": rows}


def _jsonable(params: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in params.items()}


def list_query_catalog() -> list[dict[str, object]]:
    """Every SQL file with its documentation header and full text, for the SQL explorer.

    ``runnable`` marks the queries that accept the generic dashboard parameters
    and can be executed through ``run_dashboard_query``; the others are shown
    for reading only because they need entity-specific inputs.
    """
    catalog: list[dict[str, object]] = []
    for name in query_names():
        sql = load_sql(name)
        header = [line[3:].rstrip() for line in sql.splitlines() if line.startswith("--")]
        catalog.append(
            {
                "name": name,
                "description": " ".join(header),
                "sql": sql,
                "runnable": name in DASHBOARD_QUERIES,
                "parameters": list(DASHBOARD_QUERIES.get(name, ())),
            }
        )
    return catalog


def recent_alerts(session: Session, *, limit: int = 20) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)
    return list(session.scalars(stmt))


def acknowledge_alert(session: Session, alert_id: int, *, user_id: int) -> Alert:
    alert = session.get(Alert, alert_id)
    if alert is None:
        raise NotFoundError(f"Alert {alert_id} not found")
    if alert.acknowledged_at is None:
        alert.acknowledged_at = now()
        alert.acknowledged_by = user_id
        session.flush()
    return alert
