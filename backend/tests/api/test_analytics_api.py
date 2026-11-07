from fastapi.testclient import TestClient

WINDOW = {"window_start": "2026-11-01T00:00:00", "window_end": "2026-11-05T00:00:00"}


def test_query_catalog_lists_every_sql_file(client: TestClient, viewer: dict[str, str]) -> None:
    catalog = client.get("/api/v1/analytics/queries", headers=viewer).json()
    names = {q["name"] for q in catalog}
    assert len(catalog) == 12
    assert "order_completion_summary" in names and "investigation.defect_onset" in names
    assert all(
        q["description"].startswith("Query") or "Investigation" in q["description"] for q in catalog
    )


def test_dashboard_query_returns_sql_params_and_rows(
    client: TestClient, viewer: dict[str, str], simulated: dict[str, object]
) -> None:
    body = client.get(
        "/api/v1/analytics/queries/machine_defect_rate_comparison", params=WINDOW, headers=viewer
    ).json()
    assert body["query"] == "machine_defect_rate_comparison"
    assert body["sql"].startswith("-- Query 01")
    assert body["params"]["window_start"] == "2026-11-01T00:00:00"
    assert next(r["machine_code"] for r in body["rows"]) == "CNC-03"
    rollup = client.get("/api/v1/analytics/queries/order_completion_summary", headers=viewer).json()
    assert any(r["product_name"] == "ALL" and r["status"] == "ALL" for r in rollup["rows"])


def test_only_dashboard_queries_are_exposed(client: TestClient, viewer: dict[str, str]) -> None:
    read_only = client.get("/api/v1/analytics/queries/unit_backward_trace", headers=viewer)
    assert read_only.status_code == 422
    assert "order_completion_summary" in read_only.json()["details"]["runnable_queries"]
    assert client.get("/api/v1/analytics/queries/nope", headers=viewer).status_code == 404
    inverted = client.get(
        "/api/v1/analytics/queries/daily_production_trend",
        params={"window_start": "2026-11-05T00:00:00", "window_end": "2026-11-01T00:00:00"},
        headers=viewer,
    )
    assert inverted.status_code == 422 and "window_end" in inverted.json()["message"]
    bad = client.get(
        "/api/v1/analytics/queries/batches_requiring_review",
        params={"threshold": 2},
        headers=viewer,
    )
    assert bad.status_code == 422


def test_alerts_can_be_acknowledged_once_by_operators(
    client: TestClient,
    viewer: dict[str, str],
    operator: dict[str, str],
    simulated: dict[str, object],
) -> None:
    alerts = client.get("/api/v1/analytics/alerts", headers=viewer).json()
    assert alerts and alerts[0]["acknowledged_at"] is None
    url = f"/api/v1/analytics/alerts/{alerts[0]['id']}/acknowledge"
    assert client.post(url, headers=viewer).status_code == 403
    first = client.post(url, headers=operator).json()
    second = client.post(url, headers=operator).json()
    assert first["acknowledged_at"] is not None
    assert first["acknowledged_at"] == second["acknowledged_at"]
    assert (
        client.post("/api/v1/analytics/alerts/999999/acknowledge", headers=operator).status_code
        == 404
    )


def test_quarantined_batches_drop_out_of_the_review_query(
    client: TestClient,
    engineer: dict[str, str],
    ids: dict[str, dict[str, int]],
    simulated: dict[str, object],
) -> None:
    params = {**WINDOW, "threshold": 0.10, "machine_id": ids["machines"]["CNC-03"]}
    url = "/api/v1/analytics/queries/batches_requiring_review"
    before = client.get(url, params=params, headers=engineer).json()["rows"]
    assert len(before) >= 2
    assert all(r["machine_code"] == "CNC-03" and r["defect_rate"] >= 0.10 for r in before)
    assert all(r["already_under_investigation"] == 0 for r in before)
    assert [r["defect_rate"] for r in before] == sorted(
        (r["defect_rate"] for r in before), reverse=True
    )
    worst = before[0]
    quarantined = client.post(
        f"/api/v1/production-batches/{worst['batch_id']}/quarantine",
        json={"reason": "Suspected tool wear"},
        headers=engineer,
    )
    assert quarantined.status_code == 200
    after = client.get(url, params=params, headers=engineer).json()["rows"]
    assert {r["batch_id"] for r in after} == {r["batch_id"] for r in before} - {worst["batch_id"]}
    other_machine = client.get(
        url, params={**params, "machine_id": ids["machines"]["CNC-01"]}, headers=engineer
    ).json()["rows"]
    assert other_machine == []
