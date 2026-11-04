from fastapi.testclient import TestClient

Ids = dict[str, dict[str, int]]


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
