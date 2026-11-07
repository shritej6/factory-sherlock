"""The alerts to production_orders link, concurrent checks, and the scheduled job."""

import json
import threading
from datetime import date, datetime

import pytest
from app.core.database import SessionLocal
from app.jobs import check_overdue_orders
from app.models import Alert, AlertType, OrderStatus, Product, ProductionOrder
from app.services import alert_service
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

AS_OF = datetime(2026, 11, 7, 8, 0)


def _late_order(session: Session, number: str, due: date) -> ProductionOrder:
    product_id = session.scalar(select(Product.id).where(Product.code == "GEAR"))
    order = ProductionOrder(
        order_number=number, product_id=product_id, quantity_planned=5, due_date=due
    )
    session.add(order)
    session.flush()
    return order


def _overdue_alert_count(session: Session, order_id: int) -> int:
    stmt = select(func.count(Alert.id)).where(
        Alert.production_order_id == order_id, Alert.alert_type == AlertType.ORDER_OVERDUE
    )
    return int(session.scalar(stmt) or 0)


def test_deleting_an_order_keeps_the_alert_and_clears_the_link(db_session: Session) -> None:
    order = _late_order(db_session, "PO-SETNULL", date(2026, 11, 1))
    result = alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF)
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


def test_acknowledged_alert_keeps_its_order_link(db_session: Session) -> None:
    order = _late_order(db_session, "PO-ACK", date(2026, 11, 1))
    alert = alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF).alerts[0]
    db_session.commit()
    alert.acknowledged_at = datetime(2026, 11, 7, 9, 0)
    db_session.commit()
    db_session.expire_all()
    stored = db_session.get(Alert, alert.id)
    assert stored is not None
    assert stored.production_order_id == order.id
    assert stored.acknowledged_at == datetime(2026, 11, 7, 9, 0)
    # An acknowledged alert no longer counts as open, so the order is raised again.
    assert alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF).raised == 1
    db_session.commit()
    assert _overdue_alert_count(db_session, order.id) == 2


def test_check_is_idempotent_across_sessions(db_session: Session) -> None:
    order = _late_order(db_session, "PO-TWICE", date(2026, 11, 1))
    db_session.commit()
    first = alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF)
    db_session.commit()
    second = alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF)
    db_session.commit()
    assert (first.checked, first.raised, second.checked, second.raised) == (1, 1, 1, 0)
    assert _overdue_alert_count(db_session, order.id) == 1
    order.status = OrderStatus.CANCELLED
    db_session.commit()
    assert alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF).checked == 0


def test_concurrent_checks_raise_one_alert_per_order(db_session: Session) -> None:
    """A second check that overlaps the first waits for it and then raises nothing."""
    order = _late_order(db_session, "PO-RACE", date(2026, 11, 1))
    db_session.commit()
    outcome: dict[str, int] = {}

    def second_check() -> None:
        with SessionLocal() as session:
            outcome["raised"] = alert_service.raise_overdue_order_alerts(
                session, as_of=AS_OF
            ).raised
            session.commit()

    first = alert_service.raise_overdue_order_alerts(db_session, as_of=AS_OF)
    assert first.raised == 1
    worker = threading.Thread(target=second_check)
    worker.start()
    worker.join(timeout=1.0)
    assert worker.is_alive(), "the second check must block on the locked order rows"
    db_session.commit()
    worker.join(timeout=30.0)
    assert not worker.is_alive()
    assert outcome["raised"] == 0
    assert _overdue_alert_count(db_session, order.id) == 1


def test_job_commits_and_exits_zero(
    db_session: Session, job_logger_enabled: None, capsys: pytest.CaptureFixture[str]
) -> None:
    order = _late_order(db_session, "PO-JOB", date(2026, 11, 1))
    db_session.commit()
    assert check_overdue_orders.main(["--as-of", "2026-11-07T08:00:00"]) == 0
    finished = [
        line
        for line in _json_log_lines(capsys.readouterr().out)
        if line.get("operation") == "check_overdue_orders"
    ]
    assert len(finished) == 1 and finished[0]["level"] == "INFO"
    assert '"checked": 1, "raised": 1' in str(finished[0]["message"])
    assert check_overdue_orders.main(["--as-of", "2026-11-07T09:00:00"]) == 0
    db_session.expire_all()
    alerts = list(db_session.scalars(select(Alert).where(Alert.production_order_id == order.id)))
    assert len(alerts) == 1
    assert alerts[0].created_at == datetime(2026, 11, 7, 8, 0)


def _json_log_lines(out: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


@pytest.fixture
def job_logger_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Alembic's ``fileConfig`` in the session fixture disables loggers that already exist.

    The job's module logger is one of them, so re-enable it to observe its output.
    """
    monkeypatch.setattr(check_overdue_orders.logger, "disabled", False)


def test_job_rolls_back_logs_and_exits_one_on_failure(
    db_session: Session,
    job_logger_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    order = _late_order(db_session, "PO-FAIL", date(2026, 11, 1))
    db_session.commit()

    def raise_then_fail(session: Session, *, as_of: datetime | None = None) -> None:
        session.add(
            Alert(
                production_order_id=order.id,
                alert_type=AlertType.ORDER_OVERDUE,
                severity="WARNING",
                message="must be rolled back",
            )
        )
        session.flush()
        raise RuntimeError("simulated failure after a write")

    monkeypatch.setattr(alert_service, "raise_overdue_order_alerts", raise_then_fail)
    assert check_overdue_orders.main([]) == 1
    errors = [line for line in _json_log_lines(capsys.readouterr().out) if line["level"] == "ERROR"]
    assert len(errors) == 1
    assert errors[0]["operation"] == "check_overdue_orders"
    assert "RuntimeError: simulated failure after a write" in str(errors[0]["exception"])
    assert _overdue_alert_count(db_session, order.id) == 0
