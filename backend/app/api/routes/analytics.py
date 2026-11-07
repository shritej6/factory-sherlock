from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, Operator, Paging
from app.core.clock import now
from app.schemas.analytics import OverdueCheckResponse, QueryCatalogEntry, QueryResult
from app.schemas.common import Page
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
    specification_id: int | None = Query(None, gt=0),
    threshold: float = Query(0.10, ge=0, le=1),
    hours: int = Query(3, ge=1, le=72),
    limit: int = Query(50, ge=1, le=500),
) -> QueryResult:
    start, end = _default_window(window_start, window_end)
    params = {
        "window_start": start,
        "window_end": end,
        "machine_id": machine_id,
        "specification_id": specification_id,
        "threshold": threshold,
        "hours": hours,
        "limit": limit,
    }
    return QueryResult(**analytics_service.run_dashboard_query(session, name, params))


@router.get("/alerts", response_model=Page[AlertRead])
def recent_alerts(session: DbSession, _: CurrentUser, paging: Paging) -> Page[AlertRead]:
    result = analytics_service.recent_alerts(session, paging)
    return Page[AlertRead].from_result(result, paging, AlertRead.model_validate)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge_alert(session: DbSession, user: Operator, alert_id: int) -> AlertRead:
    return AlertRead.model_validate(
        analytics_service.acknowledge_alert(session, alert_id, user_id=user.id)
    )


@router.post("/alerts/checks/overdue-orders", response_model=OverdueCheckResponse)
def check_overdue_orders(session: DbSession, _: Operator) -> OverdueCheckResponse:
    """Raise ORDER_OVERDUE alerts for open orders past their due date; safe to repeat.

    The check takes no body: due dates are judged against the server clock,
    so a client cannot choose the check date. Replaying a past check is a
    command line operation (``app.jobs.check_overdue_orders --as-of``).
    """
    result = alert_service.raise_overdue_order_alerts(session)
    return OverdueCheckResponse(
        checked=result.checked,
        raised=result.raised,
        alerts=[AlertRead.model_validate(a) for a in result.alerts],
    )
