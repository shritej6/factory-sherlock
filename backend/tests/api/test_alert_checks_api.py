"""POST /analytics/alerts/checks/overdue-orders: raising, idempotency, scope, and clock."""

from collections.abc import Callable
from datetime import date, datetime

import pytest
from app.models import OrderStatus, ProductionOrder
from app.services import alert_service
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
SetClock = Callable[[datetime], None]
URL = "/api/v1/analytics/alerts/checks/overdue-orders"
CHECK_TIME = datetime(2026, 11, 7, 8, 0)


@pytest.fixture
def set_clock(monkeypatch: pytest.MonkeyPatch) -> SetClock:
    """Pin the server clock the check reads; the endpoint has no other time input."""
    state = {"now": CHECK_TIME}
    monkeypatch.setattr(alert_service, "now", lambda: state["now"])

    def _set(moment: datetime) -> None:
        state["now"] = moment

    return _set


def _order(
    client: TestClient, headers: dict[str, str], ids: Ids, number: str, due: str, **extra: object
) -> dict[str, object]:
    body: dict[str, object] = {
        "order_number": number,
        "product_id": ids["products"]["STEEL-SHAFT"],
        "quantity_planned": 10,
        "due_date": due,
    }
    body.update(extra)
    response = client.post("/api/v1/production-orders", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


def _order_in_state(session: Session, ids: Ids, number: str, status: OrderStatus) -> int:
    """Terminal states cannot be reached from PLANNED through the API, so write the row."""
    order = ProductionOrder(
        order_number=number,
        product_id=ids["products"]["GEAR"],
        quantity_planned=5,
        quantity_completed=5 if status is OrderStatus.COMPLETED else 0,
        status=status,
        due_date=date(2026, 10, 1),
    )
    session.add(order)
    session.commit()
    return order.id


def _overdue_alerts(client: TestClient, headers: dict[str, str]) -> list[dict[str, object]]:
    alerts = client.get("/api/v1/analytics/alerts", headers=headers).json()["items"]
    return [a for a in alerts if a["alert_type"] == "ORDER_OVERDUE"]


def test_overdue_orders_raise_alerts_with_severity_by_days_late(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    set_clock: SetClock,
) -> None:
    machine = ids["machines"]["CNC-01"]
    one_day = _order(client, engineer, ids, "PO-LATE-1", "2026-11-06", machine_id=machine)
    two_days = _order(client, engineer, ids, "PO-LATE-2", "2026-11-05")
    six_days = _order(client, engineer, ids, "PO-LATE-6", "2026-11-01")

    response = client.post(URL, headers=operator)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checked"] == 3 and body["raised"] == 3
    by_order = {a["production_order_id"]: a for a in body["alerts"]}
    assert set(by_order) == {one_day["id"], two_days["id"], six_days["id"]}

    first = by_order[one_day["id"]]
    assert first["alert_type"] == "ORDER_OVERDUE"
    assert first["severity"] == "WARNING"
    assert first["machine_id"] == machine
    assert first["message"] == "Order PO-LATE-1 is 1 day overdue (due 2026-11-06)"
    assert first["created_at"] == "2026-11-07T08:00:00"
    assert first["acknowledged_at"] is None
    assert by_order[two_days["id"]]["severity"] == "WARNING"
    assert by_order[two_days["id"]]["machine_id"] is None
    assert by_order[six_days["id"]]["severity"] == "CRITICAL"
    assert (
        by_order[six_days["id"]]["message"] == "Order PO-LATE-6 is 6 days overdue (due 2026-11-01)"
    )
    assert len(_overdue_alerts(client, operator)) == 3


def test_repeated_checks_do_not_duplicate_open_alerts(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    set_clock: SetClock,
) -> None:
    _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")
    first = client.post(URL, headers=operator).json()
    second = client.post(URL, headers=operator).json()
    set_clock(datetime(2026, 11, 20, 0, 0))
    later = client.post(URL, headers=operator).json()
    assert (first["checked"], first["raised"]) == (1, 1)
    assert (second["checked"], second["raised"]) == (1, 0) and second["alerts"] == []
    assert (later["checked"], later["raised"]) == (1, 0)
    assert len(_overdue_alerts(client, operator)) == 1


def test_acknowledged_alert_lets_a_still_overdue_order_be_raised_again(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    set_clock: SetClock,
) -> None:
    order = _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")
    first = client.post(URL, headers=operator).json()["alerts"][0]
    ack = client.post(f"/api/v1/analytics/alerts/{first['id']}/acknowledge", headers=operator)
    assert ack.status_code == 200
    assert ack.json()["production_order_id"] == order["id"]
    assert ack.json()["acknowledged_at"] is not None
    set_clock(datetime(2026, 11, 10, 8, 0))
    again = client.post(URL, headers=operator).json()
    assert again["raised"] == 1
    renewed = again["alerts"][0]
    assert renewed["id"] != first["id"]
    assert renewed["production_order_id"] == order["id"]
    assert renewed["message"] == "Order PO-LATE-1 is 9 days overdue (due 2026-11-01)"
    assert renewed["severity"] == "CRITICAL"
    assert len(_overdue_alerts(client, operator)) == 2
    set_clock(datetime(2026, 11, 11, 8, 0))
    unchanged = client.post(URL, headers=operator).json()
    assert unchanged["raised"] == 0


def test_finished_orders_and_orders_due_today_are_not_overdue(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
    set_clock: SetClock,
) -> None:
    _order_in_state(db_session, ids, "PO-DONE", OrderStatus.COMPLETED)
    _order_in_state(db_session, ids, "PO-GONE", OrderStatus.CANCELLED)
    _order(client, engineer, ids, "PO-TODAY", "2026-11-07")
    _order(client, engineer, ids, "PO-FUTURE", "2026-12-01")
    _order(client, engineer, ids, "PO-NO-DUE", None)
    body = client.post(URL, headers=operator).json()
    assert body == {"checked": 0, "raised": 0, "alerts": []}
    assert _overdue_alerts(client, operator) == []


def test_check_uses_the_real_server_clock_without_a_pinned_clock(
    client: TestClient, operator: dict[str, str], engineer: dict[str, str], ids: Ids
) -> None:
    _order(client, engineer, ids, "PO-OLD", "2020-01-01")
    _order(client, engineer, ids, "PO-FAR", "2999-01-01")
    before = datetime.now().replace(microsecond=0)
    body = client.post(URL, headers=operator).json()
    assert body["checked"] == 1 and body["raised"] == 1
    assert body["alerts"][0]["message"].startswith("Order PO-OLD is ")
    created = datetime.fromisoformat(body["alerts"][0]["created_at"])
    assert before <= created <= datetime.now()


def test_client_cannot_choose_the_check_date(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    set_clock: SetClock,
) -> None:
    """A body naming a future or past as_of is ignored: no early alerts, no back-dating."""
    future_due = _order(client, engineer, ids, "PO-NOT-YET", "2026-11-30")
    late = _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")

    forged_future = client.post(URL, json={"as_of": "2999-01-01T00:00:00"}, headers=operator)
    assert forged_future.status_code == 200, forged_future.text
    body = forged_future.json()
    assert body["checked"] == 1 and body["raised"] == 1
    assert body["alerts"][0]["production_order_id"] == late["id"]
    assert body["alerts"][0]["created_at"] == "2026-11-07T08:00:00"
    assert body["alerts"][0]["message"] == "Order PO-LATE-1 is 6 days overdue (due 2026-11-01)"

    open_orders = {a["production_order_id"] for a in _overdue_alerts(client, operator)}
    assert future_due["id"] not in open_orders

    forged_past = client.post(URL, json={"as_of": "2000-01-01T00:00:00"}, headers=operator)
    assert forged_past.status_code == 200
    assert forged_past.json()["raised"] == 0
    assert {a["created_at"] for a in _overdue_alerts(client, operator)} == {"2026-11-07T08:00:00"}


def test_check_requires_operator_role(
    client: TestClient, viewer: dict[str, str], engineer: dict[str, str]
) -> None:
    assert client.post(URL, headers=viewer).status_code == 403
    assert client.post(URL).status_code == 401
    assert client.post(URL, headers=engineer).status_code == 200


def test_alert_read_exposes_the_order_link(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    set_clock: SetClock,
) -> None:
    order = _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")
    client.post(URL, headers=operator)
    listed = _overdue_alerts(client, operator)[0]
    assert listed["production_order_id"] == order["id"]
    assert listed["machine_id"] is None
