from fastapi.testclient import TestClient

Ids = dict[str, dict[str, int]]


def _set(client: TestClient, headers: dict[str, str], machine_id: int, status: str) -> object:
    return client.post(
        f"/api/v1/machines/{machine_id}/status",
        json={"status": status, "reason": f"test -> {status}"},
        headers=headers,
    )


def test_machine_state_transitions_are_enforced_and_logged(
    client: TestClient, operator: dict[str, str], ids: Ids
) -> None:
    machine = ids["machines"]["CNC-01"]
    assert _set(client, operator, machine, "RUNNING").json()["status"] == "RUNNING"  # type: ignore[attr-defined]
    assert _set(client, operator, machine, "FAULT").json()["status"] == "FAULT"  # type: ignore[attr-defined]
    rejected = _set(client, operator, machine, "RUNNING")
    assert rejected.status_code == 422  # type: ignore[attr-defined]
    assert rejected.json()["details"]["allowed"] == ["STOPPED"]  # type: ignore[attr-defined]
    assert _set(client, operator, machine, "STOPPED").json()["status"] == "STOPPED"  # type: ignore[attr-defined]
    assert _set(client, operator, machine, "IDLE").json()["status"] == "IDLE"  # type: ignore[attr-defined]

    events = client.get(f"/api/v1/machines/{machine}/events", headers=operator).json()
    assert [e["new_state"] for e in events] == ["IDLE", "STOPPED", "FAULT", "RUNNING"]
    assert events[2]["severity"] == "CRITICAL"  # the FAULT entry


def test_machine_status_change_needs_reason_and_operator_role(
    client: TestClient, viewer: dict[str, str], operator: dict[str, str], ids: Ids
) -> None:
    machine = ids["machines"]["CNC-02"]
    assert _set(client, viewer, machine, "RUNNING").status_code == 403  # type: ignore[attr-defined]
    missing = client.post(
        f"/api/v1/machines/{machine}/status", json={"status": "RUNNING"}, headers=operator
    )
    assert missing.status_code == 422


def test_create_machine_and_reject_duplicate(client: TestClient, engineer: dict[str, str]) -> None:
    body = {"code": "CNC-04", "name": "CNC Machine 04"}
    assert client.post("/api/v1/machines", json=body, headers=engineer).status_code == 201
    assert client.post("/api/v1/machines", json=body, headers=engineer).status_code == 409
    assert len(client.get("/api/v1/machines", headers=engineer).json()) == 4
