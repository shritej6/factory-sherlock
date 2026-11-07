import pytest
from app.models import Alert, MaterialLot, ProductionBatch
from app.services import traceability_service
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]


def test_forward_and_backward_trace_agree(
    client: TestClient, engineer: dict[str, str], simulated: dict[str, object]
) -> None:
    forward = client.get("/api/v1/traceability/forward/L401", headers=engineer).json()
    assert forward["lot_number"] == "L401"
    assert len(forward["batches"]) >= 1
    first = forward["batches"][0]
    assert first["units_produced"] == 30
    serial = f"{first['batch_number']}-U0001"
    backward = client.get(f"/api/v1/traceability/backward/{serial}", headers=engineer).json()
    lineage = backward["lineage"]
    assert {row["lot_number"] for row in lineage} >= {"L401"}
    assert lineage[0]["batch_number"] == first["batch_number"]
    assert lineage[0]["product_code"] == "GEAR"
    assert "outer_diameter=" in lineage[0]["inspection_summary"]


def test_unknown_lot_and_serial_return_404(client: TestClient, engineer: dict[str, str]) -> None:
    assert client.get("/api/v1/traceability/forward/L999", headers=engineer).status_code == 404
    assert client.get("/api/v1/traceability/backward/NOPE", headers=engineer).status_code == 404


def test_lot_quarantine_cascades_to_batches_in_one_transaction(
    client: TestClient, engineer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    lot_id = ids["lots"]["L401"]
    before = client.get("/api/v1/traceability/forward/L401", headers=engineer).json()["batches"]
    result = client.post(
        f"/api/v1/traceability/material-lots/{lot_id}/quarantine",
        json={"reason": "Supplier certificate withdrawn"},
        headers=engineer,
    ).json()
    assert result["lot"]["status"] == "QUARANTINED"
    assert len(result["quarantined_batches"]) == len(before)
    after = client.get("/api/v1/traceability/forward/L401", headers=engineer).json()["batches"]
    assert all(b["batch_status"] == "QUARANTINED" for b in after)
    # Second call quarantines nothing new but still succeeds.
    again = client.post(
        f"/api/v1/traceability/material-lots/{lot_id}/quarantine",
        json={"reason": "Repeated notice"},
        headers=engineer,
    ).json()
    assert again["quarantined_batches"] == []


def test_forward_trace_rows_are_ordered_and_bounded(
    client: TestClient, engineer: dict[str, str], simulated: dict[str, object]
) -> None:
    forward = client.get("/api/v1/traceability/forward/L401", headers=engineer).json()["batches"]
    assert len(forward) >= 2
    assert [b["started_at"] for b in forward] == sorted(b["started_at"] for b in forward)
    for row in forward:
        assert 0 <= row["units_failed"] <= row["units_produced"] == 30
        assert row["lot_number"] == "L401" and row["product_name"] == "Spur gear 60 mm"
        assert row["machine_code"].startswith("CNC-0")
    serial = f"{forward[0]['batch_number']}-U0001"
    lineage = client.get(f"/api/v1/traceability/backward/{serial}", headers=engineer).json()[
        "lineage"
    ]
    assert {row["machine_code"] for row in lineage} == {forward[0]["machine_code"]}
    assert [row["lot_number"] for row in lineage] == sorted(row["lot_number"] for row in lineage)


def test_lot_quarantine_records_one_critical_alert_with_the_lot_reason(
    client: TestClient, engineer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    alerts_before = len(
        client.get("/api/v1/analytics/alerts", params={"limit": 200}, headers=engineer).json()
    )
    result = client.post(
        f"/api/v1/traceability/material-lots/{ids['lots']['L401']}/quarantine",
        json={"reason": "Supplier notice"},
        headers=engineer,
    ).json()
    assert result["quarantined_batches"]
    for batch in result["quarantined_batches"]:
        assert batch["status"] == "QUARANTINED"
        assert batch["quarantine_reason"] == "Material lot L401: Supplier notice"
    alerts = client.get("/api/v1/analytics/alerts", params={"limit": 200}, headers=engineer).json()
    assert len(alerts) == alerts_before + 1
    newest = alerts[0]
    assert (newest["alert_type"], newest["severity"], newest["machine_id"]) == (
        "MATERIAL_QUARANTINE",
        "CRITICAL",
        None,
    )
    assert (
        newest["message"]
        == f"Lot L401 quarantined ({len(result['quarantined_batches'])} batches): Supplier notice"
    )


def _quarantine_state(
    session: Session, lot_id: int, batch_ids: list[int]
) -> tuple[str, set[str], int]:
    """Lot status, the distinct statuses of the given batches, and the alert count."""
    lot_status = session.scalar(select(MaterialLot.status).where(MaterialLot.id == lot_id))
    batch_statuses = session.scalars(
        select(ProductionBatch.status).where(ProductionBatch.id.in_(batch_ids))
    ).all()
    alerts = session.scalar(select(func.count(Alert.id)))
    return str(lot_status), {str(s) for s in batch_statuses}, int(alerts or 0)


def test_lot_quarantine_rolls_back_completely_when_the_alert_insert_fails(
    client: TestClient,
    engineer: dict[str, str],
    ids: Ids,
    simulated: dict[str, object],
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The alert row reuses an existing primary key, so MySQL rejects it at flush time
    after the lot and batch updates were issued in the same transaction."""
    existing_alert_id = client.get("/api/v1/analytics/alerts", headers=engineer).json()[0]["id"]
    lot_id = ids["lots"]["L401"]
    forward = client.get("/api/v1/traceability/forward/L401", headers=engineer).json()
    batch_ids = [b["batch_id"] for b in forward["batches"]]
    before = _quarantine_state(db_session, lot_id, batch_ids)
    assert before[:2] == ("AVAILABLE", {"COMPLETED"})
    monkeypatch.setattr(
        traceability_service, "Alert", lambda **kwargs: Alert(id=existing_alert_id, **kwargs)
    )

    response = client.post(
        f"/api/v1/traceability/material-lots/{lot_id}/quarantine",
        json={"reason": "Supplier certificate withdrawn"},
        headers=engineer,
    )

    assert response.status_code == 409
    assert response.json()["error"] == "ConflictError"
    assert "Duplicate" not in response.text
    assert _quarantine_state(db_session, lot_id, batch_ids) == before
    quarantined = select(func.count(ProductionBatch.id)).where(
        ProductionBatch.status == "QUARANTINED"
    )
    assert db_session.scalar(quarantined) == 0
