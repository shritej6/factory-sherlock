"""POST /api/v1/inspections/import: CSV upload, all or nothing."""

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest
from app.core.database import SessionLocal
from app.models import Inspection, ProductionUnit, ProductSpecification
from app.schemas.quality import InspectionCreate
from app.services import inspection_import, quality_service
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
Headers = dict[str, str]
URL = "/api/v1/inspections/import"
HEADER = "serial_number,characteristic,measured_value,inspected_at,defect_type_codes\n"
SEEDS_DIR = Path(__file__).resolve().parents[3] / "database" / "seeds"
# Serial numbers follow production_service.create_batch: <order>-B<nn>-U<nnnn>.
UNIT = "PO-3001-B01-U{:04d}"


def _shaft_batch(client: TestClient, engineer: Headers, ids: Ids, quantity: int = 5) -> None:
    """Five STEEL-SHAFT units with no inspections: PO-3001-B01-U0001 to U0005."""
    order = client.post(
        "/api/v1/production-orders",
        json={
            "order_number": "PO-3001",
            "product_id": ids["products"]["STEEL-SHAFT"],
            "machine_id": ids["machines"]["CNC-01"],
            "quantity_planned": quantity,
        },
        headers=engineer,
    ).json()
    client.post(
        f"/api/v1/production-orders/{order['id']}/status",
        json={"status": "RELEASED"},
        headers=engineer,
    )
    batch = client.post(
        "/api/v1/production-batches",
        json={
            "production_order_id": order["id"],
            "quantity": quantity,
            "materials": [{"material_lot_id": ids["lots"]["L201"], "quantity_used": quantity}],
        },
        headers=engineer,
    )
    assert batch.status_code == 201, batch.text
    assert batch.json()["batch_number"] == "PO-3001-B01"


def _upload(
    client: TestClient,
    headers: Headers,
    text: str,
    *,
    content_type: str = "text/csv",
    name: str = "measurements.csv",
) -> Response:
    return client.post(
        URL, files={"file": (name, text.encode("utf-8"), content_type)}, headers=headers
    )


def _errors(response: Response) -> list[dict[str, object]]:
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"] == "ValidationError"
    errors = body["details"]["errors"]
    assert isinstance(errors, list)
    return errors


def _count(db_session: Session) -> int:
    return db_session.scalar(select(func.count(Inspection.id))) or 0


def test_valid_file_is_imported_with_the_same_rules_as_manual_entry(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids, db_session: Session
) -> None:
    _shaft_batch(client, engineer, ids)
    text = HEADER + "\n".join(
        [
            f"{UNIT.format(1)},diameter,20.040,,",
            f"{UNIT.format(1)},Length,150.700,,",
            f"{UNIT.format(2)},diameter,20.250,2026-11-02T08:15:00,SURFACE_DAMAGE",
            f"{UNIT.format(2)},length,149.900,2026-11-02T08:15:00,",
            "",
            f"{UNIT.format(3)},diameter,19.850,,",
        ]
    )
    response = _upload(client, operator, text)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["imported"] == 5 and body["failed_inspections"] == 3
    assert len(body["inspection_ids"]) == 5 and len(set(body["inspection_ids"])) == 5

    listed = {
        i["id"]: i for i in client.get("/api/v1/inspections", headers=operator).json()["items"]
    }
    assert set(listed) == set(body["inspection_ids"])
    by_order = [listed[i] for i in body["inspection_ids"]]
    assert [i["result"] for i in by_order] == ["PASS", "FAIL", "FAIL", "PASS", "FAIL"]
    assert by_order[1]["defect_codes"] == ["DIMENSIONAL_DEVIATION"]
    assert by_order[2]["defect_codes"] == ["OVERSIZE_DIAMETER", "SURFACE_DAMAGE"]
    assert by_order[4]["defect_codes"] == ["UNDERSIZE_DIAMETER"]
    assert by_order[2]["inspected_at"] == "2026-11-02T08:15:00"
    # Rows without a timestamp share the request time.
    assert by_order[0]["inspected_at"] == by_order[1]["inspected_at"] == by_order[4]["inspected_at"]
    assert _count(db_session) == 5


def test_missing_required_column_is_rejected(client: TestClient, operator: Headers) -> None:
    response = _upload(client, operator, "serial_number,measured_value\nX,1\n")
    assert _errors(response) == [
        {"row": None, "field": "characteristic", "message": "Required column is missing"}
    ]


def test_unknown_column_is_rejected(client: TestClient, operator: Headers) -> None:
    response = _upload(client, operator, HEADER.rstrip("\n") + ",operator\nX,diameter,1,,,me\n")
    assert _errors(response) == [{"row": None, "field": "operator", "message": "Unknown column"}]


def test_bad_decimal_names_the_row(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids
) -> None:
    _shaft_batch(client, engineer, ids)
    response = _upload(
        client,
        operator,
        HEADER + f"{UNIT.format(1)},diameter,20.040,,\n{UNIT.format(2)},diameter,20.04x,,\n",
    )
    errors = _errors(response)
    assert len(errors) == 1
    assert (errors[0]["row"], errors[0]["field"]) == (2, "measured_value")


def test_unknown_serial_number_is_rejected(client: TestClient, operator: Headers) -> None:
    errors = _errors(_upload(client, operator, HEADER + "GHOST-0001,diameter,20.0,,\n"))
    assert errors == [
        {"row": 1, "field": "serial_number", "message": "No production unit has this serial number"}
    ]


def test_characteristic_must_belong_to_the_units_product(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids
) -> None:
    _shaft_batch(client, engineer, ids)
    # hole_position exists, but for METAL-BRACKET, not for the STEEL-SHAFT unit.
    errors = _errors(_upload(client, operator, HEADER + f"{UNIT.format(1)},hole_position,50.0,,\n"))
    assert len(errors) == 1 and (errors[0]["row"], errors[0]["field"]) == (1, "characteristic")


def test_unknown_defect_code_is_rejected(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids
) -> None:
    _shaft_batch(client, engineer, ids)
    errors = _errors(
        _upload(
            client,
            operator,
            HEADER + f"{UNIT.format(1)},diameter,20.300,,SURFACE_DAMAGE|NOT_A_CODE\n",
        )
    )
    assert errors == [
        {"row": 1, "field": "defect_type_codes", "message": "Unknown defect codes: NOT_A_CODE"}
    ]


def test_defect_codes_on_a_passing_measurement_are_rejected(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids
) -> None:
    _shaft_batch(client, engineer, ids)
    errors = _errors(
        _upload(client, operator, HEADER + f"{UNIT.format(1)},diameter,20.010,,SURFACE_DAMAGE\n")
    )
    assert errors == [
        {
            "row": 1,
            "field": "defect_type_codes",
            "message": "Defect codes cannot be attached to a passing measurement",
        }
    ]


def test_duplicate_pair_within_the_file_is_rejected(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids, db_session: Session
) -> None:
    _shaft_batch(client, engineer, ids)
    text = HEADER + f"{UNIT.format(1)},diameter,20.040,,\n{UNIT.format(1)},DIAMETER,20.050,,\n"
    errors = _errors(_upload(client, operator, text))
    assert errors == [
        {
            "row": 2,
            "field": None,
            "message": "Same serial number and characteristic as row 1 of this file",
        }
    ]
    assert _count(db_session) == 0


def test_duplicate_against_the_database_is_rejected(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids, db_session: Session
) -> None:
    _shaft_batch(client, engineer, ids)
    assert client.get("/api/v1/inspections", headers=operator).json()["items"] == []
    first = _upload(client, operator, HEADER + f"{UNIT.format(1)},diameter,20.040,,\n")
    assert first.status_code == 201
    text = HEADER + f"{UNIT.format(2)},diameter,20.040,,\n{UNIT.format(1)},diameter,20.040,,\n"
    errors = _errors(_upload(client, operator, text))
    assert errors == [
        {
            "row": 2,
            "field": None,
            "message": "This unit already has an inspection for this characteristic",
        }
    ]
    assert _count(db_session) == 1


def test_row_limit_is_enforced(client: TestClient, operator: Headers) -> None:
    text = HEADER + "".join(f"S{i},diameter,20.0,,\n" for i in range(5001))
    errors = _errors(_upload(client, operator, text))
    assert errors == [
        {"row": None, "field": "file", "message": "The file has more than 5000 data rows"}
    ]


def test_file_size_limit_is_enforced(client: TestClient, operator: Headers) -> None:
    text = HEADER + "S1,diameter,20.0,," + " " * (1024 * 1024) + "\n"
    errors = _errors(_upload(client, operator, text))
    assert errors == [{"row": None, "field": "file", "message": "The file is larger than 1024 KiB"}]


def test_viewer_cannot_import(client: TestClient, viewer: Headers) -> None:
    response = _upload(client, viewer, HEADER + "S1,diameter,20.0,,\n")
    assert response.status_code == 403
    assert response.json()["error"] == "AuthorizationError"


def test_non_csv_and_empty_uploads_are_rejected(client: TestClient, operator: Headers) -> None:
    wrong_type = _upload(
        client, operator, '{"rows": []}', content_type="application/json", name="rows.json"
    )
    assert _errors(wrong_type) == [
        {"row": None, "field": "file", "message": "Upload a CSV file with content type text/csv"}
    ]
    empty = _upload(client, operator, "")
    assert _errors(empty) == [{"row": None, "field": "file", "message": "The file is empty"}]
    # application/octet-stream is accepted for a .csv file name: the request reaches row validation.
    octet = _upload(
        client,
        operator,
        HEADER + "S1,diameter,20.0,,\n",
        content_type="application/octet-stream",
        name="gauge.csv",
    )
    assert _errors(octet)[0]["field"] == "serial_number"
    no_file = client.post(URL, data={"note": "x"}, headers=operator)
    assert no_file.status_code == 422 and no_file.json()["details"]["errors"][0]["field"] == "file"


def test_one_invalid_row_rolls_back_the_whole_file(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids, db_session: Session
) -> None:
    _shaft_batch(client, engineer, ids)
    text = HEADER + "\n".join(
        [
            f"{UNIT.format(1)},diameter,20.040,,",
            f"{UNIT.format(2)},diameter,20.040,,",
            f"{UNIT.format(3)},diameter,20.040,,",
            "GHOST-0001,diameter,20.040,,",
            f"{UNIT.format(4)},diameter,20.040,,",
        ]
    )
    errors = _errors(_upload(client, operator, text))
    assert [e["row"] for e in errors] == [4]
    assert _count(db_session) == 0
    assert client.get("/api/v1/inspections", headers=operator).json()["items"] == []


def test_sample_file_imports_against_the_demo_scenario(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids
) -> None:
    """The sample file targets the batch an operator starts for the demo order left short by downtime."""
    scenario = json.loads((SEEDS_DIR / "demo_scenario.json").read_text(encoding="utf-8"))
    scenario.pop("description")
    run = client.post("/api/v1/simulation/runs", json=scenario, headers=engineer)
    assert run.status_code == 201, run.text
    orders = client.get(
        "/api/v1/production-orders", params={"status": "IN_PROGRESS"}, headers=engineer
    ).json()["items"]
    assert [o["order_number"] for o in orders] == ["SIM0001-CNC-02-02"]
    batch = client.post(
        "/api/v1/production-batches",
        json={
            "production_order_id": orders[0]["id"],
            "quantity": 20,
            "materials": [{"material_lot_id": ids["lots"]["L302"], "quantity_used": 20}],
        },
        headers=engineer,
    )
    assert batch.status_code == 201 and batch.json()["batch_number"] == "SIM0001-CNC-02-02-B04"

    sample = (SEEDS_DIR / "sample_inspection_import.csv").read_text(encoding="utf-8")
    response = _upload(client, operator, sample, name="sample_inspection_import.csv")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["imported"] == 16 and body["failed_inspections"] == 3
    assert len(body["inspection_ids"]) == 16


def test_serial_numbers_match_without_regard_to_case(
    client: TestClient, operator: Headers, engineer: Headers, ids: Ids
) -> None:
    _shaft_batch(client, engineer, ids)
    response = _upload(client, operator, HEADER + f"{UNIT.format(1).lower()},diameter,20.040,,\n")
    assert response.status_code == 201, response.text
    assert response.json()["imported"] == 1
    listed = client.get("/api/v1/inspections", headers=operator).json()["items"]
    assert [i["id"] for i in listed] == response.json()["inspection_ids"]


def test_oversized_upload_is_rejected_with_413_before_the_route(
    client: TestClient, operator: Headers
) -> None:
    response = client.post(
        URL,
        content=b"x" * (inspection_import.MAX_FILE_BYTES + 64 * 1024 + 1),
        headers={**operator, "Content-Type": "multipart/form-data; boundary=b"},
    )
    assert response.status_code == 413
    assert response.json()["error"] == "payload_too_large"


def _between_lookups_and_write(monkeypatch: pytest.MonkeyPatch, hook: Callable[[], None]) -> None:
    """Run ``hook`` in the window another request can use: after validation, before the insert."""
    original = inspection_import._load_lookups

    def load_then_hook(session: Session, rows: list[object]) -> object:
        lookups = original(session, rows)  # type: ignore[arg-type]
        hook()
        return lookups

    monkeypatch.setattr(inspection_import, "_load_lookups", load_then_hook)


def _unit_and_spec(db_session: Session, serial: str, characteristic: str) -> tuple[int, int]:
    unit_id = db_session.scalar(
        select(ProductionUnit.id).where(ProductionUnit.serial_number == serial)
    )
    spec_id = db_session.scalar(
        select(ProductSpecification.id).where(ProductSpecification.characteristic == characteristic)
    )
    assert unit_id is not None and spec_id is not None
    db_session.rollback()
    return unit_id, spec_id


def test_pair_recorded_by_another_request_during_the_import_is_a_row_error(
    client: TestClient,
    operator: Headers,
    engineer: Headers,
    ids: Ids,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _shaft_batch(client, engineer, ids)
    unit_id, spec_id = _unit_and_spec(db_session, UNIT.format(2), "diameter")

    def record_first() -> None:
        with SessionLocal() as other:
            quality_service.record_inspection(
                other,
                InspectionCreate(
                    unit_id=unit_id, specification_id=spec_id, measured_value=Decimal("20.000")
                ),
            )
            other.commit()

    _between_lookups_and_write(monkeypatch, record_first)
    rows = [f"{UNIT.format(n)},diameter,20.040,," for n in (1, 2, 3)]
    errors = _errors(_upload(client, operator, HEADER + "\n".join(rows) + "\n"))
    assert errors == [
        {
            "row": 2,
            "field": None,
            "message": "Another import recorded this unit and characteristic first",
        }
    ]
    assert _count(db_session) == 1


def test_other_integrity_errors_are_not_mistaken_for_the_race(
    client: TestClient,
    operator: Headers,
    engineer: Headers,
    ids: Ids,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A specification deleted mid-import violates a foreign key (1452), handled by errors.py."""
    _shaft_batch(client, engineer, ids)
    _, spec_id = _unit_and_spec(db_session, UNIT.format(1), "length")

    def delete_specification() -> None:
        with SessionLocal() as other:
            other.execute(
                text("DELETE FROM product_specifications WHERE id = :id"), {"id": spec_id}
            )
            other.commit()

    _between_lookups_and_write(monkeypatch, delete_specification)
    response = _upload(client, operator, HEADER + f"{UNIT.format(1)},length,150.000,,\n")
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["message"] == "The request references a row that does not exist"
    assert body["details"] == {}
    assert _count(db_session) == 0
