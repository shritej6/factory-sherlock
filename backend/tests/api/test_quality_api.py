from app.models import ProductionUnit
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]


def _unit_and_spec(
    client: TestClient, headers: dict[str, str], ids: Ids, db_session: Session
) -> tuple[int, int, int]:
    product = next(
        p
        for p in client.get("/api/v1/products", headers=headers).json()
        if p["code"] == "STEEL-SHAFT"
    )
    spec = next(s for s in product["specifications"] if s["characteristic"] == "diameter")
    order = client.post(
        "/api/v1/production-orders",
        json={
            "order_number": "PO-3001",
            "product_id": product["id"],
            "machine_id": ids["machines"]["CNC-01"],
            "quantity_planned": 5,
        },
        headers=headers,
    ).json()
    client.post(
        f"/api/v1/production-orders/{order['id']}/status",
        json={"status": "RELEASED"},
        headers=headers,
    )
    batch = client.post(
        "/api/v1/production-batches",
        json={
            "production_order_id": order["id"],
            "quantity": 2,
            "materials": [{"material_lot_id": ids["lots"]["L201"], "quantity_used": 2}],
        },
        headers=headers,
    ).json()
    unit_id = db_session.scalar(
        select(ProductionUnit.id)
        .where(ProductionUnit.batch_id == batch["id"])
        .order_by(ProductionUnit.id)
    )
    assert unit_id is not None
    return unit_id, spec["id"], batch["id"]


def test_measurement_is_validated_against_specification(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    unit_id, spec_id, batch_id = _unit_and_spec(client, engineer, ids, db_session)
    passing = client.post(
        "/api/v1/inspections",
        json={"unit_id": unit_id, "specification_id": spec_id, "measured_value": "20.040"},
        headers=operator,
    )
    assert passing.status_code == 201 and passing.json()["result"] == "PASS"
    assert passing.json()["defect_codes"] == []

    duplicate = client.post(
        "/api/v1/inspections",
        json={"unit_id": unit_id, "specification_id": spec_id, "measured_value": "20.000"},
        headers=operator,
    )
    assert duplicate.status_code == 409  # uq_inspection_unit_spec

    summary = client.get(
        "/api/v1/quality/summary", params={"batch_id": batch_id}, headers=operator
    ).json()
    assert summary == {
        "total_produced": 2,
        "total_inspected": 1,
        "passed": 1,
        "failed": 0,
        "defect_rate": 0.0,
    }


def test_failed_measurement_is_classified(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    unit_id, spec_id, _ = _unit_and_spec(client, engineer, ids, db_session)
    failing = client.post(
        "/api/v1/inspections",
        json={
            "unit_id": unit_id,
            "specification_id": spec_id,
            "measured_value": "20.250",
            "defect_type_codes": ["SURFACE_DAMAGE"],
        },
        headers=operator,
    ).json()
    assert failing["result"] == "FAIL"
    assert failing["defect_codes"] == ["OVERSIZE_DIAMETER", "SURFACE_DAMAGE"]
    listed = client.get("/api/v1/inspections", params={"result": "FAIL"}, headers=operator).json()
    assert listed["total"] == 1 and listed["items"][0]["id"] == failing["id"]


def test_inspection_rejects_bad_references(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    unit_id, spec_id, _ = _unit_and_spec(client, engineer, ids, db_session)
    gear = next(
        p for p in client.get("/api/v1/products", headers=operator).json() if p["code"] == "GEAR"
    )
    wrong_product_spec = gear["specifications"][0]["id"]
    cases = [
        ({"unit_id": 999999, "specification_id": spec_id, "measured_value": "20.0"}, 404),
        ({"unit_id": unit_id, "specification_id": 999999, "measured_value": "20.0"}, 404),
        (
            {"unit_id": unit_id, "specification_id": wrong_product_spec, "measured_value": "20.0"},
            422,
        ),
        (
            {
                "unit_id": unit_id,
                "specification_id": spec_id,
                "measured_value": "20.0",
                "defect_type_codes": ["SURFACE_DAMAGE"],
            },
            422,
        ),
        (
            {
                "unit_id": unit_id,
                "specification_id": spec_id,
                "measured_value": "25.0",
                "defect_type_codes": ["NOT_A_CODE"],
            },
            422,
        ),
    ]
    for body, expected in cases:
        assert (
            client.post("/api/v1/inspections", json=body, headers=operator).status_code == expected
        ), body
