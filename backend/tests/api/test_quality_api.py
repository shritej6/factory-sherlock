from decimal import Decimal

from app.models import Inspection, ProductionUnit, ProductSpecification
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]


def _post_inspection(client: TestClient, headers: dict[str, str], **body: object) -> Response:
    return client.post("/api/v1/inspections", json=body, headers=headers)


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


def test_inspection_rejections_carry_the_documented_messages(
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
    wrong = _post_inspection(
        client,
        operator,
        unit_id=unit_id,
        specification_id=gear["specifications"][0]["id"],
        measured_value="60.0",
    )
    assert wrong.status_code == 422
    assert wrong.json()["message"] == "Specification does not belong to the unit's product"
    codes_on_pass = _post_inspection(
        client,
        operator,
        unit_id=unit_id,
        specification_id=spec_id,
        measured_value="20.000",
        defect_type_codes=["SURFACE_DAMAGE"],
    )
    assert codes_on_pass.status_code == 422
    message = codes_on_pass.json()["message"]
    assert message == "Defect codes cannot be attached to a passing inspection"


def test_unknown_codes_and_extra_decimals_are_named_in_the_error(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    unit_id, spec_id, _ = _unit_and_spec(client, engineer, ids, db_session)
    unknown = _post_inspection(
        client,
        operator,
        unit_id=unit_id,
        specification_id=spec_id,
        measured_value="25.0",
        defect_type_codes=["NOT_A_CODE"],
    )
    assert unknown.status_code == 422
    assert unknown.json()["message"] == "Unknown defect codes: ['NOT_A_CODE']"
    four_decimals = _post_inspection(
        client, operator, unit_id=unit_id, specification_id=spec_id, measured_value="20.0001"
    )
    assert four_decimals.status_code == 422
    assert four_decimals.json()["details"]["errors"][0]["field"] == "measured_value"


def test_tolerance_boundary_through_the_api(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    first_unit, spec_id, batch_id = _unit_and_spec(client, engineer, ids, db_session)
    second_unit = db_session.scalars(
        select(ProductionUnit.id)
        .where(ProductionUnit.batch_id == batch_id)
        .order_by(ProductionUnit.id)
    ).all()[1]
    on_limit = _post_inspection(
        client, operator, unit_id=first_unit, specification_id=spec_id, measured_value="20.100"
    ).json()
    beyond = _post_inspection(
        client, operator, unit_id=second_unit, specification_id=spec_id, measured_value="20.101"
    ).json()
    assert (on_limit["result"], on_limit["defect_codes"]) == ("PASS", [])
    assert (beyond["result"], beyond["defect_codes"]) == ("FAIL", ["OVERSIZE_DIAMETER"])
    assert Decimal(beyond["measured_value"]) == Decimal("20.101")
    summary = client.get(
        "/api/v1/quality/summary", params={"batch_id": batch_id}, headers=operator
    ).json()
    assert (summary["total_inspected"], summary["failed"], summary["defect_rate"]) == (2, 1, 0.5)


def test_stored_result_survives_a_specification_change(
    client: TestClient,
    operator: dict[str, str],
    engineer: dict[str, str],
    ids: Ids,
    db_session: Session,
) -> None:
    unit_id, spec_id, _ = _unit_and_spec(client, engineer, ids, db_session)
    recorded = _post_inspection(
        client, operator, unit_id=unit_id, specification_id=spec_id, measured_value="20.090"
    ).json()
    assert recorded["result"] == "PASS"
    spec = db_session.get(ProductSpecification, spec_id)
    assert spec is not None
    spec.tolerance = Decimal("0.010")  # tightened after the fact; 20.090 would now fail
    db_session.commit()
    stored = client.get("/api/v1/inspections", headers=operator).json()["items"]
    assert [i["result"] for i in stored if i["id"] == recorded["id"]] == ["PASS"]
    assert (
        db_session.scalar(select(Inspection.result).where(Inspection.id == recorded["id"]))
        == "PASS"
    )
