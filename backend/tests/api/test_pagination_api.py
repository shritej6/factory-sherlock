"""Offset pagination contract shared by the growth-table list endpoints."""

import pytest
from fastapi.testclient import TestClient

Ids = dict[str, dict[str, int]]
ENVELOPE_KEYS = {"items", "total", "limit", "offset"}


def _create_orders(client: TestClient, headers: dict[str, str], ids: Ids, count: int) -> list[int]:
    created = []
    for index in range(count):
        body = {
            "order_number": f"PO-PAGE-{index:02d}",
            "product_id": ids["products"]["STEEL-SHAFT"],
            "quantity_planned": 10,
        }
        response = client.post("/api/v1/production-orders", json=body, headers=headers)
        assert response.status_code == 201, response.text
        created.append(response.json()["id"])
    return created


def _page(client: TestClient, headers: dict[str, str], url: str, **params: object) -> dict:  # type: ignore[type-arg]
    response = client.get(url, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_list_endpoints_default_to_limit_50_and_offset_0(
    client: TestClient, viewer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    urls = [
        "/api/v1/production-orders",
        "/api/v1/production-batches",
        "/api/v1/inspections",
        "/api/v1/investigations",
        f"/api/v1/machines/{ids['machines']['CNC-03']}/events",
        "/api/v1/analytics/alerts",
    ]
    for url in urls:
        body = _page(client, viewer, url)
        assert set(body) == ENVELOPE_KEYS, url
        assert body["limit"] == 50 and body["offset"] == 0, url
        assert len(body["items"]) == min(body["total"], 50), url


def test_pages_are_stable_disjoint_and_cover_every_order(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    created = _create_orders(client, engineer, ids, 5)
    everything = _page(client, engineer, "/api/v1/production-orders", limit=500)
    all_ids = [o["id"] for o in everything["items"]]
    # Orders created in the same second share created_at, so id is the tiebreaker.
    assert all_ids == sorted(created, reverse=True)

    pages = [
        _page(client, engineer, "/api/v1/production-orders", limit=2, offset=offset)
        for offset in (0, 2, 4)
    ]
    assert [p["total"] for p in pages] == [5, 5, 5]
    assert [(p["limit"], p["offset"]) for p in pages] == [(2, 0), (2, 2), (2, 4)]
    assert [len(p["items"]) for p in pages] == [2, 2, 1]
    paged_ids = [o["id"] for p in pages for o in p["items"]]
    assert paged_ids == all_ids


def test_offset_past_the_end_returns_empty_items_with_total(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    _create_orders(client, engineer, ids, 3)
    body = _page(client, engineer, "/api/v1/production-orders", limit=10, offset=100)
    assert body == {"items": [], "total": 3, "limit": 10, "offset": 100}


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 501},
        {"limit": -1},
        {"offset": -1},
        {"offset": 1_000_001},
        {"limit": "ten"},
    ],
)
def test_invalid_paging_values_are_rejected(
    client: TestClient, viewer: dict[str, str], ids: Ids, params: dict[str, object]
) -> None:
    urls = [
        "/api/v1/production-orders",
        "/api/v1/production-batches",
        "/api/v1/inspections",
        "/api/v1/investigations",
        f"/api/v1/machines/{ids['machines']['CNC-01']}/events",
        "/api/v1/analytics/alerts",
    ]
    for url in urls:
        response = client.get(url, params=params, headers=viewer)
        assert response.status_code == 422, (url, params)


def test_status_filter_applies_before_paging(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    created = _create_orders(client, engineer, ids, 5)
    for order_id in created[:2]:
        response = client.post(
            f"/api/v1/production-orders/{order_id}/status",
            json={"status": "CANCELLED"},
            headers=engineer,
        )
        assert response.status_code == 200, response.text
    body = _page(client, engineer, "/api/v1/production-orders", status="PLANNED", limit=2)
    assert body["total"] == 3 and len(body["items"]) == 2
    assert all(o["status"] == "PLANNED" for o in body["items"])
    rest = _page(client, engineer, "/api/v1/production-orders", status="PLANNED", limit=2, offset=2)
    assert rest["total"] == 3 and len(rest["items"]) == 1
    assert _page(client, engineer, "/api/v1/production-orders")["total"] == 5


def test_batch_and_inspection_filters_combine_with_paging(
    client: TestClient, viewer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    machine_id = ids["machines"]["CNC-03"]
    on_machine = _page(
        client, viewer, "/api/v1/production-batches", machine_id=machine_id, limit=500
    )
    assert on_machine["total"] == len(on_machine["items"]) == 8
    first_page = _page(client, viewer, "/api/v1/production-batches", machine_id=machine_id, limit=3)
    assert first_page["total"] == 8 and len(first_page["items"]) == 3
    assert all(b["machine_id"] == machine_id for b in first_page["items"])
    order_id = first_page["items"][0]["production_order_id"]
    expected = sum(1 for b in on_machine["items"] if b["production_order_id"] == order_id)
    by_order = _page(client, viewer, "/api/v1/production-batches", order_id=order_id, limit=500)
    assert 0 < by_order["total"] == len(by_order["items"]) == expected < 8

    failed = _page(client, viewer, "/api/v1/inspections", result="FAIL", limit=5)
    assert failed["total"] == simulated["failed_inspections"]
    assert len(failed["items"]) == 5
    assert all(i["result"] == "FAIL" for i in failed["items"])
    all_inspections = _page(client, viewer, "/api/v1/inspections", limit=1)
    assert all_inspections["total"] == simulated["inspections_created"]
    assert all_inspections["total"] > failed["total"]


def test_offset_at_the_upper_bound_is_accepted(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    _create_orders(client, engineer, ids, 1)
    body = _page(client, engineer, "/api/v1/production-orders", limit=10, offset=1_000_000)
    assert body == {"items": [], "total": 1, "limit": 10, "offset": 1_000_000}
