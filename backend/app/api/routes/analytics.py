from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, Operator
from app.core.clock import now
from app.schemas.analytics import (
    OverdueCheckRequest,
    OverdueCheckResponse,
    QueryCatalogEntry,
    QueryResult,
)
from app.schemas.investigation import AlertRead
from app.services import alert_service, analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _default_window(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    end = end or now() + timedelta(days=1)
    start = start or end - timedelta(days=30)
    return start, end


@router.get("/queries", response_model=list[QueryCatalogEntry])
def list_queries(_: CurrentUser) -> list[QueryCatalogEntry]:
    return [QueryCatalogEntry(**entry) for entry in analytics_service.list_query_catalog()]


@router.get("/queries/{name}", response_model=QueryResult)
def run_query(
    session: DbSession,
    _: CurrentUser,
    name: str,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    machine_id: int | None = Query(None, gt=0),
    threshold: float = Query(0.10, ge=0, le=1),
    hours: int = Query(3, ge=1, le=72),
    limit: int = Query(50, ge=1, le=500),
) -> QueryResult:
    start, end = _default_window(window_start, window_end)
    params = {
        "window_start": start,
        "window_end": end,
        "machine_id": machine_id,
        "threshold": threshold,
        "hours": hours,
        "limit": limit,
    }
    return QueryResult(**analytics_service.run_dashboard_query(session, name, params))


@router.get("/alerts", response_model=list[AlertRead])
def recent_alerts(
    session: DbSession, _: CurrentUser, limit: int = Query(20, ge=1, le=200)
) -> list[AlertRead]:
    return [
        AlertRead.model_validate(a) for a in analytics_service.recent_alerts(session, limit=limit)
    ]


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(session: DbSession, user: Operator, alert_id: int) -> AlertRead:
    return AlertRead.model_validate(
        analytics_service.acknowledge_alert(session, alert_id, user_id=user.id)
    )


@router.post("/alerts/checks/overdue-orders", response_model=OverdueCheckResponse)
def check_overdue_orders(
    session: DbSession, _: Operator, body: OverdueCheckRequest | None = None
) -> OverdueCheckResponse:
    """Raise ORDER_OVERDUE alerts for open orders past their due date; safe to repeat."""
    as_of = body.as_of if body is not None else None
    result = alert_service.raise_overdue_order_alerts(session, as_of=as_of)
    return OverdueCheckResponse(
        checked=result.checked,
        raised=result.raised,
        alerts=[AlertRead.model_validate(a) for a in result.alerts],
    )
