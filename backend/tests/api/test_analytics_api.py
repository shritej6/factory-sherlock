from fastapi.testclient import TestClient

WINDOW = {"window_start": "2026-11-01T00:00:00", "window_end": "2026-11-05T00:00:00"}


def test_query_catalog_lists_every_sql_file(client: TestClient, viewer: dict[str, str]) -> None:
    catalog = client.get("/api/v1/analytics/queries", headers=viewer).json()
    names = {q["name"] for q in catalog}
    assert len(catalog) == 13
    assert "order_completion_summary" in names and "investigation.defect_onset" in names
    assert all(
        q["description"].startswith("Query") or "Investigation" in q["description"] for q in catalog
    )
    chart = next(q for q in catalog if q["name"] == "characteristic_control_chart")
    assert chart["runnable"] is True
    assert chart["parameters"] == ["specification_id", "window_start", "window_end", "machine_id"]
    read_only = next(q for q in catalog if q["name"] == "unit_backward_trace")
    assert read_only["runnable"] is False and read_only["parameters"] == []


def _diameter_spec(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    specs = client.get("/api/v1/specifications", headers=headers).json()
    return next(
        s for s in specs if s["product_code"] == "STEEL-SHAFT" and s["characteristic"] == "diameter"
    )


def test_specifications_are_listed_flat_for_every_role(
    client: TestClient, viewer: dict[str, str]
) -> None:
    response = client.get("/api/v1/specifications", headers=viewer)
    assert response.status_code == 200
    specs = response.json()
    assert len(specs) == 6
    assert set(specs[0]) == {
        "id",
        "product_id",
        "product_code",
        "characteristic",
        "target_value",
        "tolerance",
        "unit",
    }
    assert [s["product_code"] for s in specs] == sorted(s["product_code"] for s in specs)
    diameter = _diameter_spec(client, viewer)
    assert diameter["target_value"] == "20.000" and diameter["tolerance"] == "0.100"
    assert client.get("/api/v1/specifications").status_code == 401


def test_control_chart_requires_specification_id(
    client: TestClient, viewer: dict[str, str], ids: dict[str, dict[str, int]]
) -> None:
    missing = client.get(
        "/api/v1/analytics/queries/characteristic_control_chart", params=WINDOW, headers=viewer
    )
    assert missing.status_code == 422
    assert "specification_id" in missing.json()["message"]
    zero = client.get(
        "/api/v1/analytics/queries/characteristic_control_chart",
        params={**WINDOW, "specification_id": 0},
        headers=viewer,
    )
    assert zero.status_code == 422
    other_query = client.get(
        "/api/v1/analytics/queries/daily_production_trend",
        params={**WINDOW, "specification_id": 1},
        headers=viewer,
    )
    assert other_query.status_code == 200
    assert "specification_id" not in other_query.json()["params"]


def test_control_chart_runs_with_specification_and_machine_filter(
    client: TestClient,
    viewer: dict[str, str],
    ids: dict[str, dict[str, int]],
    simulated: dict[str, object],
) -> None:
    spec_id = _diameter_spec(client, viewer)["id"]
    url = "/api/v1/analytics/queries/characteristic_control_chart"
    body = client.get(url, params={**WINDOW, "specification_id": spec_id}, headers=viewer).json()
    assert body["query"] == "characteristic_control_chart"
    assert body["sql"].startswith("-- Query 10")
    assert body["params"] == {
        "specification_id": spec_id,
        "window_start": "2026-11-01T00:00:00",
        "window_end": "2026-11-05T00:00:00",
        "machine_id": None,
    }
    assert body["rows"] and all(r["machine_code"] == "CNC-03" for r in body["rows"])
    first = body["rows"][0]
    assert first["lower_spec_limit"] == 19.9 and first["upper_spec_limit"] == 20.1
    assert first["lcl"] < first["grand_mean"] < first["ucl"]

    filtered = client.get(
        url,
        params={**WINDOW, "specification_id": spec_id, "machine_id": ids["machines"]["CNC-03"]},
        headers=viewer,
    ).json()
    assert filtered["params"]["machine_id"] == ids["machines"]["CNC-03"]
    assert filtered["rows"] == body["rows"]
    other = client.get(
        url,
        params={**WINDOW, "specification_id": spec_id, "machine_id": ids["machines"]["CNC-01"]},
        headers=viewer,
    ).json()
    assert other["rows"] == []


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
    alerts = client.get("/api/v1/analytics/alerts", headers=viewer).json()["items"]
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
