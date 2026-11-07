"""POST /analytics/alerts/checks/overdue-orders: raising, idempotency, and scope."""

from datetime import date

from app.models import OrderStatus, ProductionOrder
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
URL = "/api/v1/analytics/alerts/checks/overdue-orders"
AS_OF = {"as_of": "2026-11-07T08:00:00"}


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
    client: TestClient, operator: dict[str, str], engineer: dict[str, str], ids: Ids
) -> None:
    machine = ids["machines"]["CNC-01"]
    one_day = _order(client, engineer, ids, "PO-LATE-1", "2026-11-06", machine_id=machine)
    two_days = _order(client, engineer, ids, "PO-LATE-2", "2026-11-05")
    six_days = _order(client, engineer, ids, "PO-LATE-6", "2026-11-01")

    response = client.post(URL, json=AS_OF, headers=operator)
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
    client: TestClient, operator: dict[str, str], engineer: dict[str, str], ids: Ids
) -> None:
    _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")
    first = client.post(URL, json=AS_OF, headers=operator).json()
    second = client.post(URL, json=AS_OF, headers=operator).json()
    later = client.post(URL, json={"as_of": "2026-11-20T00:00:00"}, headers=operator).json()
    assert (first["checked"], first["raised"]) == (1, 1)
    assert (second["checked"], second["raised"]) == (1, 0) and second["alerts"] == []
    assert (later["checked"], later["raised"]) == (1, 0)
    assert len(_overdue_alerts(client, operator)) == 1


def test_acknowledged_alert_lets_a_still_overdue_order_be_raised_again(
    client: TestClient, operator: dict[str, str], engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")
    first = client.post(URL, json=AS_OF, headers=operator).json()["alerts"][0]
    ack = client.post(f"/api/v1/analytics/alerts/{first['id']}/acknowledge", headers=operator)
    assert ack.status_code == 200
    again = client.post(URL, json={"as_of": "2026-11-10T08:00:00"}, headers=operator).json()
    assert again["raised"] == 1
    renewed = again["alerts"][0]
    assert renewed["id"] != first["id"]
    assert renewed["production_order_id"] == order["id"]
    assert renewed["message"] == "Order PO-LATE-1 is 9 days overdue (due 2026-11-01)"
    assert renewed["severity"] == "CRITICAL"
    assert len(_overdue_alerts(client, operator)) == 2
    unchanged = client.post(URL, json={"as_of": "2026-11-11T08:00:00"}, headers=operator).json()
    assert unchanged["raised"] == 0


def test_finished_orders_and_orders_due_today_are_not_overdue(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    _order_in_state(db_session, ids, "PO-DONE", OrderStatus.COMPLETED)
    _order_in_state(db_session, ids, "PO-GONE", OrderStatus.CANCELLED)
    _order(client, engineer, ids, "PO-TODAY", "2026-11-07")
    _order(client, engineer, ids, "PO-FUTURE", "2026-12-01")
    _order(client, engineer, ids, "PO-NO-DUE", None)
    body = client.post(URL, json=AS_OF, headers=operator).json()
    assert body == {"checked": 0, "raised": 0, "alerts": []}
    assert _overdue_alerts(client, operator) == []


def test_default_as_of_is_the_server_clock(
    client: TestClient, operator: dict[str, str], engineer: dict[str, str], ids: Ids
) -> None:
    _order(client, engineer, ids, "PO-OLD", "2020-01-01")
    _order(client, engineer, ids, "PO-FAR", "2999-01-01")
    body = client.post(URL, headers=operator).json()
    assert body["checked"] == 1 and body["raised"] == 1
    assert body["alerts"][0]["message"].startswith("Order PO-OLD is ")


def test_check_requires_operator_role_and_rejects_unknown_fields(
    client: TestClient, viewer: dict[str, str], engineer: dict[str, str], operator: dict[str, str]
) -> None:
    assert client.post(URL, json=AS_OF, headers=viewer).status_code == 403
    assert client.post(URL, json=AS_OF).status_code == 401
    assert client.post(URL, json=AS_OF, headers=engineer).status_code == 200
    assert client.post(URL, json={"as_of": "not a date"}, headers=operator).status_code == 422
    assert client.post(URL, json={"since": "2026-11-07"}, headers=operator).status_code == 422


def test_alert_read_exposes_the_order_link(
    client: TestClient, operator: dict[str, str], engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids, "PO-LATE-1", "2026-11-01")
    client.post(URL, json=AS_OF, headers=operator)
    listed = _overdue_alerts(client, operator)[0]
    assert listed["production_order_id"] == order["id"]
    assert listed["machine_id"] is None
