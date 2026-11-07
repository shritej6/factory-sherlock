from app.models import BatchMaterial, ProductionBatch, ProductionUnit
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]


def _released_order(client: TestClient, headers: dict[str, str], ids: Ids, qty: int = 20) -> int:
    body = {
        "order_number": "PO-2001",
        "product_id": ids["products"]["STEEL-SHAFT"],
        "machine_id": ids["machines"]["CNC-02"],
        "quantity_planned": qty,
    }
    order_id = client.post("/api/v1/production-orders", json=body, headers=headers).json()["id"]
    client.post(
        f"/api/v1/production-orders/{order_id}/status", json={"status": "RELEASED"}, headers=headers
    )
    return order_id


def _batch_body(order_id: int, ids: Ids, qty: int = 8, lots: tuple[str, ...] = ("L201",)) -> dict:  # type: ignore[type-arg]
    return {
        "production_order_id": order_id,
        "quantity": qty,
        "materials": [{"material_lot_id": ids["lots"][lot], "quantity_used": qty} for lot in lots],
    }


def test_batch_creation_writes_batch_units_and_materials_together(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    order_id = _released_order(client, engineer, ids)
    response = client.post(
        "/api/v1/production-batches",
        json=_batch_body(order_id, ids, lots=("L201", "L202")),
        headers=operator,
    )
    assert response.status_code == 201, response.text
    batch = response.json()
    assert batch["batch_number"] == "PO-2001-B01"
    assert batch["status"] == "IN_PROGRESS"
    assert {m["material_lot_id"] for m in batch["material_links"]} == {
        ids["lots"]["L201"],
        ids["lots"]["L202"],
    }
    units = db_session.scalar(
        select(func.count(ProductionUnit.id)).where(ProductionUnit.batch_id == batch["id"])
    )
    assert units == 8
    order = client.get(f"/api/v1/production-orders/{order_id}", headers=operator).json()
    assert order["status"] == "IN_PROGRESS"  # first batch moves the order forward


def test_batch_with_unavailable_lot_leaves_nothing_behind(
    client: TestClient, engineer: dict[str, str], ids: Ids, db_session: Session
) -> None:
    """Transaction rollback: the lot check fails after the order was moved to
    IN_PROGRESS in the same session, so the order must still read RELEASED."""
    order_id = _released_order(client, engineer, ids)
    lot_id = ids["lots"]["L403"]
    client.post(
        f"/api/v1/traceability/material-lots/{lot_id}/quarantine",
        json={"reason": "supplier recall"},
        headers=engineer,
    )
    response = client.post(
        "/api/v1/production-batches",
        json=_batch_body(order_id, ids, lots=("L201", "L403")),
        headers=engineer,
    )
    assert response.status_code == 422
    assert "QUARANTINED" in response.json()["message"]
    assert db_session.scalar(select(func.count(ProductionBatch.id))) == 0
    assert db_session.scalar(select(func.count(BatchMaterial.batch_id))) == 0
    assert (
        client.get(f"/api/v1/production-orders/{order_id}", headers=engineer).json()["status"]
        == "RELEASED"
    )


def test_batch_cannot_exceed_remaining_quantity(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order_id = _released_order(client, engineer, ids, qty=10)
    assert (
        client.post(
            "/api/v1/production-batches", json=_batch_body(order_id, ids, qty=6), headers=engineer
        ).status_code
        == 201
    )
    too_many = client.post(
        "/api/v1/production-batches", json=_batch_body(order_id, ids, qty=5), headers=engineer
    )
    assert too_many.status_code == 422
    assert "4 units" in too_many.json()["message"]


def test_duplicate_lots_and_unknown_lots_are_rejected(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order_id = _released_order(client, engineer, ids)
    dup = _batch_body(order_id, ids, lots=("L201", "L201"))
    assert client.post("/api/v1/production-batches", json=dup, headers=engineer).status_code == 422
    unknown = _batch_body(order_id, ids)
    unknown["materials"][0]["material_lot_id"] = 999999
    assert (
        client.post("/api/v1/production-batches", json=unknown, headers=engineer).status_code == 404
    )


def test_completing_batches_completes_the_order(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order_id = _released_order(client, engineer, ids, qty=10)
    first = client.post(
        "/api/v1/production-batches", json=_batch_body(order_id, ids, qty=6), headers=engineer
    ).json()
    second = client.post(
        "/api/v1/production-batches", json=_batch_body(order_id, ids, qty=4), headers=engineer
    ).json()
    assert (
        client.post(f"/api/v1/production-batches/{first['id']}/complete", headers=engineer).json()[
            "status"
        ]
        == "COMPLETED"
    )
    assert (
        client.get(f"/api/v1/production-orders/{order_id}", headers=engineer).json()[
            "quantity_completed"
        ]
        == 6
    )
    assert (
        client.post(f"/api/v1/production-batches/{second['id']}/complete", headers=engineer).json()[
            "status"
        ]
        == "COMPLETED"
    )
    order = client.get(f"/api/v1/production-orders/{order_id}", headers=engineer).json()
    assert (order["quantity_completed"], order["status"]) == (10, "COMPLETED")
    # Completing twice is an invalid transition.
    assert (
        client.post(
            f"/api/v1/production-batches/{first['id']}/complete", headers=engineer
        ).status_code
        == 422
    )


def test_quarantine_batch_records_reason_and_alert(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order_id = _released_order(client, engineer, ids)
    batch = client.post(
        "/api/v1/production-batches", json=_batch_body(order_id, ids), headers=engineer
    ).json()
    short = client.post(
        f"/api/v1/production-batches/{batch['id']}/quarantine",
        json={"reason": "bad"},
        headers=engineer,
    )
    assert short.status_code == 422  # reason too short
    done = client.post(
        f"/api/v1/production-batches/{batch['id']}/quarantine",
        json={"reason": "Oversize diameters found"},
        headers=engineer,
    ).json()
    assert (
        done["status"] == "QUARANTINED" and done["quarantine_reason"] == "Oversize diameters found"
    )
    alerts = client.get("/api/v1/analytics/alerts", headers=engineer).json()["items"]
    assert alerts[0]["alert_type"] == "MATERIAL_QUARANTINE"
    # A quarantined batch cannot be completed.
    assert (
        client.post(
            f"/api/v1/production-batches/{batch['id']}/complete", headers=engineer
        ).status_code
        == 422
    )


def test_cancelled_order_rejects_batch_completion(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order_id = _released_order(client, engineer, ids, qty=10)
    batch = client.post(
        "/api/v1/production-batches", json=_batch_body(order_id, ids, qty=10), headers=engineer
    ).json()
    cancel = client.post(
        f"/api/v1/production-orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=engineer,
    )
    assert cancel.status_code == 200
    done = client.post(f"/api/v1/production-batches/{batch['id']}/complete", headers=engineer)
    assert done.status_code == 422
    assert "CANCELLED" in done.json()["message"]
    order = client.get(f"/api/v1/production-orders/{order_id}", headers=engineer).json()
    assert order["status"] == "CANCELLED" and order["quantity_completed"] == 0


def test_quarantine_is_idempotent(client: TestClient, engineer: dict[str, str], ids: Ids) -> None:
    order_id = _released_order(client, engineer, ids, qty=5)
    batch = client.post(
        "/api/v1/production-batches", json=_batch_body(order_id, ids, qty=5), headers=engineer
    ).json()
    url = f"/api/v1/production-batches/{batch['id']}/quarantine"
    first = client.post(url, json={"reason": "Suspect surface finish"}, headers=engineer).json()
    second = client.post(url, json={"reason": "Second notice"}, headers=engineer)
    assert second.status_code == 200
    assert second.json()["quarantine_reason"] == first["quarantine_reason"]
    alerts = client.get("/api/v1/analytics/alerts", headers=engineer).json()["items"]
    assert sum(1 for a in alerts if batch["batch_number"] in a["message"]) == 1


def test_released_order_keeps_its_machine(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    order_id = _released_order(client, engineer, ids, qty=5)
    response = client.patch(
        f"/api/v1/production-orders/{order_id}", json={"machine_id": None}, headers=engineer
    )
    assert response.status_code == 422
    assert "machine" in response.json()["message"]
