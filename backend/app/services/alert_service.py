"""Alert checks that run on demand rather than inside another workflow.

Today there is one: the overdue order check. It is idempotent per open alert,
so a scheduler can call it as often as it likes; an order gets a second
ORDER_OVERDUE alert only after the first one has been acknowledged and the
order is still not finished.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now
from app.models import Alert, AlertType, OrderStatus, ProductionOrder, Severity

# COMPLETED and CANCELLED are the terminal states of ORDER_TRANSITIONS; an
# order in either can no longer become late.
OPEN_ORDER_STATES = frozenset(OrderStatus) - {OrderStatus.COMPLETED, OrderStatus.CANCELLED}

# Days late at which an overdue alert stops being a WARNING and becomes CRITICAL.
CRITICAL_AFTER_DAYS = 2


@dataclass(frozen=True)
class OverdueCheckResult:
    """``checked`` counts overdue open orders; ``raised`` counts new alerts among them."""

    checked: int
    raised: int
    alerts: list[Alert]


def days_late(due_date: date, as_of: datetime) -> int:
    """Whole calendar days between the due date and the check date; 0 or less is not late.

    ``due_date`` is a DATE, so an order is overdue only once the check date is
    past it: an order due today is on time until midnight.
    """
    return (as_of.date() - due_date).days


def overdue_severity(days: int) -> Severity:
    """WARNING for the first ``CRITICAL_AFTER_DAYS`` days late, CRITICAL from the next day on."""
    return Severity.WARNING if days <= CRITICAL_AFTER_DAYS else Severity.CRITICAL


def overdue_message(order_number: str, due_date: date, days: int) -> str:
    unit = "day" if days == 1 else "days"
    return f"Order {order_number} is {days} {unit} overdue (due {due_date.isoformat()})"


def _naive(moment: datetime) -> datetime:
    """Match the schema's naive local DATETIME columns and drop microseconds like ``clock.now``."""
    if moment.tzinfo is not None:
        moment = moment.astimezone().replace(tzinfo=None)
    return moment.replace(microsecond=0)


def overdue_orders(session: Session, *, as_of: datetime) -> list[ProductionOrder]:
    stmt = (
        select(ProductionOrder)
        .where(
            ProductionOrder.due_date < as_of.date(),
            ProductionOrder.status.in_(OPEN_ORDER_STATES),
        )
        .order_by(ProductionOrder.due_date, ProductionOrder.id)
    )
    return list(session.scalars(stmt))


def _orders_with_open_alert(session: Session, order_ids: list[int]) -> set[int]:
    if not order_ids:
        return set()
    stmt = select(Alert.production_order_id).where(
        Alert.alert_type == AlertType.ORDER_OVERDUE,
        Alert.acknowledged_at.is_(None),
        Alert.production_order_id.in_(order_ids),
    )
    return {order_id for order_id in session.scalars(stmt) if order_id is not None}


def raise_overdue_order_alerts(
    session: Session, *, as_of: datetime | None = None
) -> OverdueCheckResult:
    """Raise one ORDER_OVERDUE alert per overdue order that has no open overdue alert.

    The alert is stamped with ``as_of`` so a check replayed for an earlier
    moment sorts into the alert feed at that moment. The caller commits.
    """
    moment = _naive(as_of or now())
    orders = overdue_orders(session, as_of=moment)
    already_open = _orders_with_open_alert(session, [order.id for order in orders])
    raised: list[Alert] = []
    for order in orders:
        if order.id in already_open or order.due_date is None:
            continue
        days = days_late(order.due_date, moment)
        alert = Alert(
            machine_id=order.machine_id,
            production_order_id=order.id,
            alert_type=AlertType.ORDER_OVERDUE,
            severity=overdue_severity(days),
            message=overdue_message(order.order_number, order.due_date, days),
            created_at=moment,
        )
        session.add(alert)
        raised.append(alert)
    session.flush()
    return OverdueCheckResult(checked=len(orders), raised=len(raised), alerts=raised)
