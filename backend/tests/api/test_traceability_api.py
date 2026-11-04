from fastapi.testclient import TestClient

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
