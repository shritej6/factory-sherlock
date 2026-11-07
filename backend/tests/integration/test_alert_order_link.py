"""The alerts to production_orders link: SET NULL on delete, and the scheduled job."""

from datetime import date, datetime

from app.jobs import check_overdue_orders
from app.models import Alert, AlertType, OrderStatus, Product, ProductionOrder
from app.services import alert_service
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session


def _late_order(session: Session, number: str, due: date) -> ProductionOrder:
    product_id = session.scalar(select(Product.id).where(Product.code == "GEAR"))
    order = ProductionOrder(
        order_number=number, product_id=product_id, quantity_planned=5, due_date=due
    )
    session.add(order)
    session.flush()
    return order


def test_deleting_an_order_keeps_the_alert_and_clears_the_link(db_session: Session) -> None:
    order = _late_order(db_session, "PO-SETNULL", date(2026, 11, 1))
    result = alert_service.raise_overdue_order_alerts(db_session, as_of=datetime(2026, 11, 7, 8, 0))
    db_session.commit()
    assert result.raised == 1
    alert_id = result.alerts[0].id
    assert db_session.get(Alert, alert_id) is not None

    # The order has no batches, so RESTRICT does not apply; the alert must survive.
    db_session.execute(text("DELETE FROM production_orders WHERE id = :id"), {"id": order.id})
    db_session.commit()
    db_session.expire_all()
    alert = db_session.get(Alert, alert_id)
    assert alert is not None
    assert alert.production_order_id is None
    assert alert.alert_type is AlertType.ORDER_OVERDUE
    assert alert.message == "Order PO-SETNULL is 6 days overdue (due 2026-11-01)"


def test_check_is_idempotent_across_sessions(db_session: Session) -> None:
    order = _late_order(db_session, "PO-TWICE", date(2026, 11, 1))
    db_session.commit()
    as_of = datetime(2026, 11, 7, 8, 0)
    first = alert_service.raise_overdue_order_alerts(db_session, as_of=as_of)
    db_session.commit()
    second = alert_service.raise_overdue_order_alerts(db_session, as_of=as_of)
    db_session.commit()
    assert (first.checked, first.raised, second.checked, second.raised) == (1, 1, 1, 0)
    count = db_session.scalar(
        select(func.count(Alert.id)).where(Alert.production_order_id == order.id)
    )
    assert count == 1
    order.status = OrderStatus.CANCELLED
    db_session.commit()
    assert alert_service.raise_overdue_order_alerts(db_session, as_of=as_of).checked == 0


def test_job_commits_and_exits_zero(db_session: Session) -> None:
    order = _late_order(db_session, "PO-JOB", date(2026, 11, 1))
    db_session.commit()
    assert check_overdue_orders.main(["--as-of", "2026-11-07T08:00:00"]) == 0
    assert check_overdue_orders.main(["--as-of", "2026-11-07T09:00:00"]) == 0
    db_session.expire_all()
    alerts = list(db_session.scalars(select(Alert).where(Alert.production_order_id == order.id)))
    assert len(alerts) == 1
    assert alerts[0].created_at == datetime(2026, 11, 7, 8, 0)
