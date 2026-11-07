"""Server-side status filters, the order status-counts endpoint, and batch order numbers.

These replace client-side filtering over 500-row lookups and the six-request
fan-out the frontend used to count orders per status.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from app.core.database import engine
from app.models.enums import OrderStatus
from fastapi.testclient import TestClient
from sqlalchemy import event

Ids = dict[str, dict[str, int]]
Headers = dict[str, str]
WINDOW = {"window_start": "2026-11-02T00:00:00", "window_end": "2026-11-04T00:00:00"}


@contextmanager
def count_statements() -> Iterator[list[str]]:
    """Collect every SQL statement the engine sends while the block runs."""
    statements: list[str] = []

    def record(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def _page(client: TestClient, headers: Headers, url: str, **params: object) -> dict[str, Any]:
    response = client.get(url, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _order(client: TestClient, headers: Headers, ids: Ids, number: str, **overrides: object) -> int:
    body: dict[str, object] = {
        "order_number": number,
        "product_id": ids["products"]["STEEL-SHAFT"],
        "quantity_planned": 20,
        **overrides,
    }
    response = client.post("/api/v1/production-orders", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _set_order_status(client: TestClient, headers: Headers, order_id: int, status: str) -> None:
    response = client.post(
        f"/api/v1/production-orders/{order_id}/status", json={"status": status}, headers=headers
    )
    assert response.status_code == 200, response.text


def _batch(client: TestClient, headers: Headers, ids: Ids, order_id: int, qty: int = 5) -> int:
    body = {
        "production_order_id": order_id,
        "quantity": qty,
        "materials": [{"material_lot_id": ids["lots"]["L201"], "quantity_used": qty}],
    }
    response = client.post("/api/v1/production-batches", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
def batch_mix(client: TestClient, engineer: Headers, ids: Ids) -> dict[str, list[int]]:
    """Two orders on two machines; CNC-02 ends with one batch in each status."""
    first = _order(client, engineer, ids, "PO-F-01", machine_id=ids["machines"]["CNC-02"])
    second = _order(client, engineer, ids, "PO-F-02", machine_id=ids["machines"]["CNC-01"])
    for order_id in (first, second):
        _set_order_status(client, engineer, order_id, "RELEASED")
    in_progress = _batch(client, engineer, ids, first)
    completed = _batch(client, engineer, ids, first)
    quarantined = _batch(client, engineer, ids, first)
    other_machine = _batch(client, engineer, ids, second)
    done = client.post(f"/api/v1/production-batches/{completed}/complete", headers=engineer)
    assert done.status_code == 200, done.text
    response = client.post(
        f"/api/v1/production-batches/{quarantined}/quarantine",
        json={"reason": "Suspect surface finish"},
        headers=engineer,
    )
    assert response.status_code == 200, response.text
    return {
        "IN_PROGRESS": [in_progress, other_machine],
        "COMPLETED": [completed],
        "QUARANTINED": [quarantined],
    }


def test_batches_filter_by_one_status(
    client: TestClient, viewer: Headers, batch_mix: dict[str, list[int]]
) -> None:
    page = _page(client, viewer, "/api/v1/production-batches", status="COMPLETED")
    assert page["total"] == 1
    assert [b["id"] for b in page["items"]] == batch_mix["COMPLETED"]
    assert page["items"][0]["status"] == "COMPLETED"


def test_batches_filter_by_two_statuses_means_any_of(
    client: TestClient, viewer: Headers, batch_mix: dict[str, list[int]]
) -> None:
    page = _page(
        client,
        viewer,
        "/api/v1/production-batches",
        status=["IN_PROGRESS", "QUARANTINED"],
        limit=500,
    )
    expected = set(batch_mix["IN_PROGRESS"]) | set(batch_mix["QUARANTINED"])
    assert page["total"] == len(expected) == 3
    assert {b["id"] for b in page["items"]} == expected
    assert {b["status"] for b in page["items"]} == {"IN_PROGRESS", "QUARANTINED"}


def test_batches_status_total_reflects_filter_before_paging(
    client: TestClient, viewer: Headers, batch_mix: dict[str, list[int]]
) -> None:
    page = _page(
        client,
        viewer,
        "/api/v1/production-batches",
        status=["IN_PROGRESS", "QUARANTINED"],
        limit=1,
    )
    assert page["total"] == 3 and len(page["items"]) == 1
    assert _page(client, viewer, "/api/v1/production-batches")["total"] == 4


def test_batches_status_filter_combines_with_machine_filter(
    client: TestClient, viewer: Headers, ids: Ids, batch_mix: dict[str, list[int]]
) -> None:
    page = _page(
        client,
        viewer,
        "/api/v1/production-batches",
        status="IN_PROGRESS",
        machine_id=ids["machines"]["CNC-01"],
    )
    assert page["total"] == 1
    assert page["items"][0]["id"] == batch_mix["IN_PROGRESS"][1]
    assert page["items"][0]["machine_id"] == ids["machines"]["CNC-01"]


@pytest.mark.parametrize("value", ["DONE", "completed", "", ["COMPLETED", "nope"]])
def test_batches_invalid_status_is_rejected(
    client: TestClient, viewer: Headers, value: object
) -> None:
    response = client.get("/api/v1/production-batches", params={"status": value}, headers=viewer)
    assert response.status_code == 422, response.text
    assert response.json()["error"] == "ValidationError"


def test_batch_list_and_detail_carry_the_order_number(
    client: TestClient, viewer: Headers, batch_mix: dict[str, list[int]]
) -> None:
    listed = _page(client, viewer, "/api/v1/production-batches", limit=500)["items"]
    by_id = {b["id"]: b for b in listed}
    assert by_id[batch_mix["COMPLETED"][0]]["order_number"] == "PO-F-01"
    assert by_id[batch_mix["IN_PROGRESS"][1]]["order_number"] == "PO-F-02"
    assert all(b["batch_number"].startswith(b["order_number"] + "-B") for b in listed)
    detail = client.get(
        f"/api/v1/production-batches/{batch_mix['QUARANTINED'][0]}", headers=viewer
    ).json()
    assert detail["order_number"] == "PO-F-01"


def test_batch_list_loads_order_numbers_without_a_query_per_row(
    client: TestClient, viewer: Headers, simulated: dict[str, object]
) -> None:
    """The statement count must not grow with the number of rows on the page."""
    with count_statements() as one_row:
        small = _page(client, viewer, "/api/v1/production-batches", limit=1)
    with count_statements() as every_row:
        full = _page(client, viewer, "/api/v1/production-batches", limit=500)
    assert full["total"] == len(full["items"]) == 24
    assert len(small["items"]) == 1
    assert all(b["order_number"] for b in full["items"])
    assert len(every_row) == len(one_row)
    assert sum("FROM production_orders" in s for s in every_row) == 1


@pytest.fixture
def investigation_mix(client: TestClient, engineer: Headers) -> dict[str, int]:
    created = {}
    for status in ("OPEN", "IN_REVIEW", "CLOSED"):
        response = client.post(
            "/api/v1/investigations",
            json={"title": f"Case {status}", **WINDOW},
            headers=engineer,
        )
        assert response.status_code == 201, response.text
        created[status] = response.json()["id"]
    url = f"/api/v1/investigations/{created['IN_REVIEW']}/status"
    assert client.post(url, json={"status": "IN_REVIEW"}, headers=engineer).status_code == 200
    url = f"/api/v1/investigations/{created['CLOSED']}/status"
    assert client.post(url, json={"status": "IN_REVIEW"}, headers=engineer).status_code == 200
    closing = {"status": "CLOSED", "conclusion": "No issue found."}
    assert client.post(url, json=closing, headers=engineer).status_code == 200
    return created


def test_investigations_filter_by_one_status(
    client: TestClient, viewer: Headers, investigation_mix: dict[str, int]
) -> None:
    page = _page(client, viewer, "/api/v1/investigations", status="OPEN")
    assert page["total"] == 1
    assert [i["id"] for i in page["items"]] == [investigation_mix["OPEN"]]


def test_investigations_filter_by_two_statuses_and_total(
    client: TestClient, viewer: Headers, investigation_mix: dict[str, int]
) -> None:
    page = _page(client, viewer, "/api/v1/investigations", status=["OPEN", "IN_REVIEW"], limit=1)
    assert page["total"] == 2 and len(page["items"]) == 1
    assert page["items"][0]["status"] in {"OPEN", "IN_REVIEW"}
    everything = _page(client, viewer, "/api/v1/investigations", status=["OPEN", "IN_REVIEW"])
    assert {i["id"] for i in everything["items"]} == {
        investigation_mix["OPEN"],
        investigation_mix["IN_REVIEW"],
    }
    assert _page(client, viewer, "/api/v1/investigations")["total"] == 3


@pytest.mark.parametrize("value", ["ARCHIVED", "open", ["OPEN", "ARCHIVED"]])
def test_investigations_invalid_status_is_rejected(
    client: TestClient, viewer: Headers, value: object
) -> None:
    response = client.get("/api/v1/investigations", params={"status": value}, headers=viewer)
    assert response.status_code == 422, response.text


def test_order_status_counts_lists_every_status_even_when_empty(
    client: TestClient, viewer: Headers
) -> None:
    response = client.get("/api/v1/production-orders/status-counts", headers=viewer)
    assert response.status_code == 200, response.text
    assert response.json() == {status.value: 0 for status in OrderStatus}


def test_order_status_counts_match_the_list_totals(
    client: TestClient, engineer: Headers, ids: Ids, simulated: dict[str, object]
) -> None:
    _order(client, engineer, ids, "PO-C-01")
    _order(client, engineer, ids, "PO-C-02")
    released = _order(client, engineer, ids, "PO-C-03", machine_id=ids["machines"]["CNC-01"])
    _set_order_status(client, engineer, released, "RELEASED")
    cancelled = _order(client, engineer, ids, "PO-C-04")
    _set_order_status(client, engineer, cancelled, "CANCELLED")

    counts = client.get("/api/v1/production-orders/status-counts", headers=engineer).json()
    assert set(counts) == {status.value for status in OrderStatus}
    for status, count in counts.items():
        listed = _page(client, engineer, "/api/v1/production-orders", status=status, limit=1)
        assert count == listed["total"], status
    assert counts["PLANNED"] == 2 and counts["RELEASED"] == 1 and counts["CANCELLED"] == 1
    assert counts["COMPLETED"] + counts["IN_PROGRESS"] > 0
    assert sum(counts.values()) == _page(client, engineer, "/api/v1/production-orders")["total"]


def test_order_status_counts_is_not_captured_by_the_order_id_route(
    client: TestClient, viewer: Headers
) -> None:
    response = client.get("/api/v1/production-orders/status-counts", headers=viewer)
    assert response.status_code == 200
    assert "id" not in response.json()
    assert client.get("/api/v1/production-orders/status-counts").status_code == 401
