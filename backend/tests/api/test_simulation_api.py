import pymysql
import pytest
from app.models import (
    Alert,
    Inspection,
    MachineEvent,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
)
from app.services import simulation_service
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
SMALL_RUN = {
    "start_time": "2026-11-05T08:00:00",
    "batches_per_machine": 2,
    "units_per_batch": 5,
    "faults": [{"machine_code": "CNC-02", "fault": "TOOL_WEAR", "start_batch_index": 1}],
}


def _next_run_tag(client: TestClient, headers: dict[str, str]) -> str:
    orders = client.get("/api/v1/production-orders", headers=headers).json()
    return f"SIM{len(orders) + 1:04d}"


def _per_serial_results(
    client: TestClient, headers: dict[str, str], run_tag: str
) -> list[tuple[str, str]]:
    """(serial without the run tag, inspection summary) for every unit of one run, via the API."""
    batches = [
        b
        for b in client.get("/api/v1/production-batches", headers=headers).json()
        if b["batch_number"].startswith(f"{run_tag}-")
    ]
    assert len(batches) == 6
    rows: list[tuple[str, str]] = []
    for batch in batches:
        for seq in range(1, batch["quantity"] + 1):
            serial = f"{batch['batch_number']}-U{seq:04d}"
            trace = client.get(f"/api/v1/traceability/backward/{serial}", headers=headers).json()
            summary = trace["lineage"][0]["inspection_summary"]
            assert " PASS" in summary or " FAIL" in summary
            rows.append((serial.removeprefix(run_tag), summary))
    return sorted(rows)


def test_simulation_persists_consistent_counts(
    client: TestClient, engineer: dict[str, str], simulated: dict[str, object]
) -> None:
    assert simulated["batches_created"] == 24  # 3 machines x 8 batches
    assert simulated["units_created"] == 720
    assert simulated["inspections_created"] == 1440  # two specifications per product
    assert simulated["events_created"] >= 7
    summary = client.get("/api/v1/quality/summary", headers=engineer).json()
    assert summary["total_produced"] == 720
    assert summary["failed"] == simulated["failed_inspections"]
    machines = {
        m["code"]: m["status"] for m in client.get("/api/v1/machines", headers=engineer).json()
    }
    assert machines == {"CNC-01": "IDLE", "CNC-02": "IDLE", "CNC-03": "WARNING"}


def test_simulation_is_deterministic_across_runs(
    client: TestClient, engineer: dict[str, str]
) -> None:
    body = {
        "seed": 99,
        "start_time": "2026-11-05T08:00:00",
        "batches_per_machine": 2,
        "units_per_batch": 5,
    }
    first = client.post("/api/v1/simulation/runs", json=body, headers=engineer).json()
    second = client.post("/api/v1/simulation/runs", json=body, headers=engineer).json()
    assert first["failed_inspections"] == second["failed_inspections"]
    orders = client.get("/api/v1/production-orders", headers=engineer).json()
    assert len(orders) == 6
    assert {o["order_number"][:7] for o in orders} == {"SIM0001", "SIM0004"}


def test_same_seed_reproduces_every_measured_value_and_result_per_serial(
    client: TestClient, engineer: dict[str, str]
) -> None:
    runs = []
    for seed in (99, 99, 100):
        tag = _next_run_tag(client, engineer)
        result = client.post(
            "/api/v1/simulation/runs", json={"seed": seed, **SMALL_RUN}, headers=engineer
        )
        assert result.status_code == 201, result.text
        runs.append(_per_serial_results(client, engineer, tag))
    first, second, other_seed = runs
    assert len(first) == 30  # 3 machines x 2 batches x 5 units
    assert first == second
    assert [serial for serial, _ in first] == [serial for serial, _ in other_seed]  # same structure
    assert first != other_seed  # different measurements


def test_simulation_refuses_to_run_without_available_lots(
    client: TestClient, engineer: dict[str, str], ids: Ids
) -> None:
    for lot in ("L401", "L402", "L403"):
        client.post(
            f"/api/v1/traceability/material-lots/{ids['lots'][lot]}/quarantine",
            json={"reason": "Supplier recall"},
            headers=engineer,
        )
    response = client.post(
        "/api/v1/simulation/runs", json={"seed": 1, **SMALL_RUN}, headers=engineer
    )
    assert response.status_code == 422
    assert response.json()["message"] == "No available material lots for product GEAR"


def test_failed_persistence_leaves_no_simulated_rows(
    client: TestClient,
    engineer: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    """The alert insert is the last write of persist(); failing it must undo everything before it."""

    def duplicate_alert(**kwargs: object) -> Alert:
        raise IntegrityError(
            "INSERT INTO alerts", kwargs, pymysql.err.IntegrityError(1062, "Duplicate entry")
        )

    monkeypatch.setattr(simulation_service, "Alert", duplicate_alert)
    body = {
        "seed": 7,
        "start_time": "2026-11-02T06:00:00",
        "batches_per_machine": 8,
        "units_per_batch": 30,
        "faults": [{"machine_code": "CNC-03", "fault": "TOOL_WEAR", "start_batch_index": 2}],
    }
    response = client.post("/api/v1/simulation/runs", json=body, headers=engineer)
    assert response.status_code == 409
    for model in (
        ProductionOrder,
        ProductionBatch,
        ProductionUnit,
        Inspection,
        MachineEvent,
        Alert,
    ):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    machines = {
        m["code"]: m["status"] for m in client.get("/api/v1/machines", headers=engineer).json()
    }
    assert machines == {"CNC-01": "IDLE", "CNC-02": "IDLE", "CNC-03": "IDLE"}


def test_simulation_validates_input(
    client: TestClient, engineer: dict[str, str], operator: dict[str, str]
) -> None:
    base = {"seed": 1, "start_time": "2026-11-05T08:00:00"}
    assert client.post("/api/v1/simulation/runs", json=base, headers=operator).status_code == 403
    unknown_fault = {
        **base,
        "faults": [{"machine_code": "CNC-01", "fault": "GREMLINS", "start_batch_index": 0}],
    }
    assert (
        client.post("/api/v1/simulation/runs", json=unknown_fault, headers=engineer).status_code
        == 422
    )
    unknown_machine = {
        **base,
        "faults": [{"machine_code": "CNC-77", "fault": "TOOL_WEAR", "start_batch_index": 0}],
    }
    assert (
        client.post("/api/v1/simulation/runs", json=unknown_machine, headers=engineer).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/simulation/runs", json={**base, "units_per_batch": 0}, headers=engineer
        ).status_code
        == 422
    )


def test_duplicate_and_out_of_range_faults_are_rejected(
    client: TestClient, engineer: dict[str, str]
) -> None:
    base = {"seed": 1, "start_time": "2026-11-05T08:00:00", "batches_per_machine": 4}
    duplicate = {
        **base,
        "faults": [
            {"machine_code": "CNC-01", "fault": "TOOL_WEAR", "start_batch_index": 1},
            {"machine_code": "CNC-01", "fault": "DOWNTIME", "start_batch_index": 1},
        ],
    }
    response = client.post("/api/v1/simulation/runs", json=duplicate, headers=engineer)
    assert response.status_code == 422
    assert "Duplicate fault" in response.json()["details"]["errors"][0]["message"]
    beyond = {
        **base,
        "faults": [{"machine_code": "CNC-01", "fault": "TOOL_WEAR", "start_batch_index": 4}],
    }
    assert client.post("/api/v1/simulation/runs", json=beyond, headers=engineer).status_code == 422
