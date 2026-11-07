from fastapi.testclient import TestClient

Ids = dict[str, dict[str, int]]


def _order(client: TestClient, headers: dict[str, str], ids: Ids, **overrides: object) -> dict:  # type: ignore[type-arg]
    body = {
        "order_number": "PO-1001",
        "product_id": ids["products"]["STEEL-SHAFT"],
        "quantity_planned": 40,
    }
    body.update(overrides)
    response = client.post("/api/v1/production-orders", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_valid_order_creation(client: TestClient, engineer: dict[str, str], ids: Ids) -> None:
    order = _order(client, engineer, ids, due_date="2026-12-01")
    assert order["status"] == "PLANNED"
    assert order["quantity_completed"] == 0
    assert order["machine_id"] is None


def test_created_order_is_stored_and_read_back_unchanged(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(
        client,
        engineer,
        ids,
        order_number="PO-TEST-001",
        machine_id=ids["machines"]["CNC-01"],
        due_date="2026-11-30",
    )
    assert order["status"] == "PLANNED" and order["quantity_completed"] == 0
    assert order["machine_id"] == ids["machines"]["CNC-01"]
    assert order["due_date"] == "2026-11-30"
    assert order["created_at"] is not None and "." not in order["created_at"]
    stored = client.get(f"/api/v1/production-orders/{order['id']}", headers=engineer).json()
    assert stored == order


def test_unknown_order_fields_and_viewer_creation_are_rejected(
    client: TestClient, engineer: dict[str, str], viewer: dict[str, str], ids: Ids
) -> None:
    body = {
        "order_number": "PO-1",
        "product_id": ids["products"]["STEEL-SHAFT"],
        "quantity_planned": 5,
    }
    unknown = client.post(
        "/api/v1/production-orders", json={**body, "priority": 1}, headers=engineer
    )
    assert unknown.status_code == 422
    assert [e["field"] for e in unknown.json()["details"]["errors"]] == ["priority"]
    forbidden = client.post("/api/v1/production-orders", json=body, headers=viewer)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"] == "AuthorizationError"
    assert forbidden.json()["details"]["required"] == ["ADMIN", "ENGINEER"]


def test_planned_quantity_upper_bound(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    _order(client, engineer, ids, order_number="PO-MAX", quantity_planned=100_000)
    body = {
        "order_number": "PO-OVER",
        "product_id": ids["products"]["GEAR"],
        "quantity_planned": 100_001,
    }
    response = client.post("/api/v1/production-orders", json=body, headers=engineer)
    assert response.status_code == 422
    assert [e["field"] for e in response.json()["details"]["errors"]] == ["quantity_planned"]


def test_order_cannot_complete_before_all_units_are_produced(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids, machine_id=ids["machines"]["CNC-01"], quantity_planned=10)
    url = f"/api/v1/production-orders/{order['id']}"
    client.post(f"{url}/status", json={"status": "RELEASED"}, headers=engineer)
    batch = {
        "production_order_id": order["id"],
        "quantity": 4,
        "materials": [{"material_lot_id": ids["lots"]["L201"], "quantity_used": 4}],
    }
    created = client.post("/api/v1/production-batches", json=batch, headers=engineer).json()
    client.post(f"/api/v1/production-batches/{created['id']}/complete", headers=engineer)
    premature = client.post(f"{url}/status", json={"status": "COMPLETED"}, headers=engineer)
    assert premature.status_code == 422
    assert premature.json()["error"] == "ValidationError"
    assert "4 of 10 units produced" in premature.json()["message"]


def test_orders_are_editable_only_while_planned_or_released(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids, machine_id=ids["machines"]["CNC-01"], quantity_planned=10)
    url = f"/api/v1/production-orders/{order['id']}"
    assert client.patch(url, json={"quantity_planned": 12}, headers=engineer).status_code == 200
    client.post(f"{url}/status", json={"status": "RELEASED"}, headers=engineer)
    released = client.patch(url, json={"due_date": "2026-12-24"}, headers=engineer)
    assert released.status_code == 200 and released.json()["due_date"] == "2026-12-24"
    batch = {
        "production_order_id": order["id"],
        "quantity": 2,
        "materials": [{"material_lot_id": ids["lots"]["L201"], "quantity_used": 2}],
    }
    assert (
        client.post("/api/v1/production-batches", json=batch, headers=engineer).status_code == 201
    )
    in_progress = client.patch(url, json={"quantity_planned": 20}, headers=engineer)
    assert in_progress.status_code == 422
    assert "IN_PROGRESS" in in_progress.json()["message"]


def test_invalid_orders_are_rejected(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    product = ids["products"]["STEEL-SHAFT"]
    cases = [
        {"order_number": "PO-1", "product_id": product, "quantity_planned": 0},
        {"order_number": "PO-1", "product_id": product, "quantity_planned": -5},
        {"order_number": "lower case", "product_id": product, "quantity_planned": 5},
        {"order_number": "PO-1", "product_id": 999999, "quantity_planned": 5},
        {
            "order_number": "PO-1",
            "product_id": product,
            "quantity_planned": 5,
            "machine_id": 999999,
        },
    ]
    statuses = [
        client.post("/api/v1/production-orders", json=c, headers=engineer).status_code
        for c in cases
    ]
    assert statuses == [422, 422, 422, 404, 404]


def test_duplicate_order_number_conflicts(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    _order(client, engineer, ids)
    body = {"order_number": "PO-1001", "product_id": ids["products"]["GEAR"], "quantity_planned": 1}
    response = client.post("/api/v1/production-orders", json=body, headers=engineer)
    assert response.status_code == 409
    assert response.json()["error"] == "ConflictError"


def test_release_requires_machine_then_lifecycle_runs(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids)
    url = f"/api/v1/production-orders/{order['id']}"
    blocked = client.post(f"{url}/status", json={"status": "RELEASED"}, headers=engineer)
    assert blocked.status_code == 422 and "machine" in blocked.json()["message"]

    assert (
        client.patch(
            url, json={"machine_id": ids["machines"]["CNC-01"]}, headers=engineer
        ).status_code
        == 200
    )
    assert (
        client.post(f"{url}/status", json={"status": "RELEASED"}, headers=engineer).json()["status"]
        == "RELEASED"
    )
    premature = client.post(f"{url}/status", json={"status": "COMPLETED"}, headers=engineer)
    assert premature.status_code == 422  # RELEASED -> COMPLETED is not a legal transition


def test_cancelled_order_cannot_start_production(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids, machine_id=ids["machines"]["CNC-01"])
    url = f"/api/v1/production-orders/{order['id']}"
    assert (
        client.post(f"{url}/status", json={"status": "CANCELLED"}, headers=engineer).status_code
        == 200
    )
    for target in ("RELEASED", "IN_PROGRESS"):
        response = client.post(f"{url}/status", json={"status": target}, headers=engineer)
        assert response.status_code == 422
        assert response.json()["error"] == "InvalidTransitionError"
    batch = {
        "production_order_id": order["id"],
        "quantity": 5,
        "materials": [{"material_lot_id": ids["lots"]["L201"], "quantity_used": 5}],
    }
    assert (
        client.post("/api/v1/production-batches", json=batch, headers=engineer).status_code == 422
    )
    # Cancelled orders cannot be edited either.
    assert client.patch(url, json={"quantity_planned": 10}, headers=engineer).status_code == 422


def test_viewer_sees_orders_but_cannot_change_status(
    client: TestClient, engineer: dict[str, str], viewer: dict[str, str], ids: Ids
) -> None:
    order = _order(client, engineer, ids)
    assert len(client.get("/api/v1/production-orders", headers=viewer).json()) == 1
    url = f"/api/v1/production-orders/{order['id']}/status"
    assert client.post(url, json={"status": "CANCELLED"}, headers=viewer).status_code == 403
