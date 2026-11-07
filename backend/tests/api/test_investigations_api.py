from fastapi.testclient import TestClient

Ids = dict[str, dict[str, int]]
WINDOW = {"window_start": "2026-11-02T00:00:00", "window_end": "2026-11-04T00:00:00"}


def test_high_defect_rate_is_detected_with_evidence(
    client: TestClient, engineer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    body = {"title": "CNC-03 drift", "machine_id": ids["machines"]["CNC-03"], **WINDOW}
    response = client.post("/api/v1/investigations", json=body, headers=engineer)
    assert response.status_code == 201, response.text
    inv = response.json()
    codes = [e["rule_code"] for e in inv["evidence"]]
    assert codes == ["R1", "R2", "R3", "R4", "R5", "R6"]
    assert "elevated defect rate" in inv["summary"]
    assert "Oversized diameter" in inv["summary"]
    assert "TOOL_WEAR" in inv["summary"]
    assert len(inv["batch_links"]) >= 1
    r1 = inv["evidence"][0]
    assert r1["query_name"] == "machine_defect_rate_comparison"
    assert r1["query_sql"].startswith("-- Query 01")
    assert any(
        row["machine_code"] == "CNC-03" and row["defect_rank"] == 1 for row in r1["result_rows"]
    )
    assert inv["evidence"][3]["result_rows"][0]["event_type"] == "TOOL_WEAR"


def test_healthy_machine_is_not_flagged(
    client: TestClient, engineer: dict[str, str], ids: Ids, simulated: dict[str, object]
) -> None:
    body = {"title": "CNC-01 check", "machine_id": ids["machines"]["CNC-01"], **WINDOW}
    inv = client.post("/api/v1/investigations", json=body, headers=engineer).json()
    assert "in line with" in inv["evidence"][0]["narrative"]
    assert inv["batch_links"] == []
    assert "No action is indicated" in inv["summary"]


def test_investigation_lifecycle_and_validation(
    client: TestClient, engineer: dict[str, str], operator: dict[str, str], ids: Ids
) -> None:
    bad_window = {
        "title": "x",
        "machine_id": ids["machines"]["CNC-01"],
        "window_start": "2026-11-04T00:00:00",
        "window_end": "2026-11-02T00:00:00",
    }
    assert (
        client.post("/api/v1/investigations", json=bad_window, headers=engineer).status_code == 422
    )
    assert (
        client.post(
            "/api/v1/investigations", json={"title": "x", **WINDOW}, headers=operator
        ).status_code
        == 403
    )

    inv = client.post(
        "/api/v1/investigations", json={"title": "Fleet review", **WINDOW}, headers=engineer
    ).json()
    url = f"/api/v1/investigations/{inv['id']}/status"
    assert (
        client.post(url, json={"status": "CLOSED"}, headers=engineer).status_code == 422
    )  # needs conclusion
    assert (
        client.post(url, json={"status": "IN_REVIEW"}, headers=engineer).json()["status"]
        == "IN_REVIEW"
    )
    closed = client.post(
        url, json={"status": "CLOSED", "conclusion": "No issue found."}, headers=engineer
    ).json()
    assert closed["status"] == "CLOSED" and closed["closed_at"] is not None
    assert client.post(url, json={"status": "OPEN"}, headers=engineer).status_code == 422
    listed = client.get("/api/v1/investigations", headers=operator).json()
    assert listed["total"] == 1 and len(listed["items"]) == 1


def test_evidence_rows_keep_sql_column_order(
    client: TestClient,
    engineer: dict[str, str],
    simulated: dict[str, object],
    ids: dict[str, dict[str, int]],
) -> None:
    body = {
        "title": "Column order check",
        "machine_id": ids["machines"]["CNC-03"],
        "window_start": "2026-11-01T00:00:00",
        "window_end": "2026-11-05T00:00:00",
    }
    inv = client.post("/api/v1/investigations", json=body, headers=engineer).json()
    r1 = inv["evidence"][0]
    assert list(r1["result_rows"][0].keys())[:3] == ["machine_id", "machine_code", "machine_name"]
    assert "T" in inv["evidence"][2]["result_rows"][0]["bucket_start"]
    assert "." not in inv["created_at"]
