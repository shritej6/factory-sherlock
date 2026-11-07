"""Every documented SQL file runs against simulated data and returns sane shapes."""

from datetime import datetime
from math import sqrt

from app.models import Inspection
from app.repositories.query_runner import SqlQueryRunner
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
WINDOW = {"window_start": datetime(2026, 11, 1), "window_end": datetime(2026, 11, 5)}
CONTROL_CHART_COLUMNS = [
    "batch_id",
    "batch_number",
    "machine_code",
    "subgroup_start",
    "sample_count",
    "mean_value",
    "std_dev",
    "min_value",
    "max_value",
    "target_value",
    "lower_spec_limit",
    "upper_spec_limit",
    "grand_mean",
    "ucl",
    "lcl",
]


def _diameter_spec_id(client: TestClient, headers: dict[str, str]) -> int:
    specs = client.get("/api/v1/specifications", headers=headers).json()
    spec = next(
        s for s in specs if s["product_code"] == "STEEL-SHAFT" and s["characteristic"] == "diameter"
    )
    return int(spec["id"])


def test_all_queries_run_and_agree(
    db_session: Session,
    client: TestClient,
    engineer: dict[str, str],
    ids: Ids,
    simulated: dict[str, object],
) -> None:
    runner = SqlQueryRunner(db_session)
    cnc3 = ids["machines"]["CNC-03"]

    rates = runner.run("machine_defect_rate_comparison", WINDOW)
    assert rates[0]["machine_code"] == "CNC-03"
    assert sum(r["failed"] for r in rates) == simulated["failed_inspections"]
    assert all(r["fleet_defect_rate"] == rates[0]["fleet_defect_rate"] for r in rates)

    perf = runner.run("production_performance", {"limit": 50})
    assert len(perf) == 6 and all(p["completion_pct"] == 100.0 for p in perf)

    defects = runner.run("recurring_defects", {**WINDOW, "machine_id": cnc3})
    assert (
        defects[0]["defect_code"] == "OVERSIZE_DIAMETER" and defects[0]["rank_within_machine"] == 1
    )
    assert abs(sum(d["share_of_machine_defects"] for d in defects) - 1.0) < 0.01

    forward = runner.run("material_lot_forward_trace", {"lot_number": "L201"})
    assert forward and all(f["units_produced"] == 30 for f in forward)
    serial = f"{forward[0]['batch_number']}-U0003"
    backward = runner.run("unit_backward_trace", {"serial_number": serial})
    assert (
        backward[0]["serial_number"] == serial and "diameter=" in backward[0]["inspection_summary"]
    )

    events = runner.run("quality_after_machine_events", {**WINDOW, "machine_id": cnc3, "hours": 3})
    assert len(events) == 1 and events[0]["event_type"] == "TOOL_WEAR"
    assert events[0]["rate_after"] > events[0]["rate_before"]

    rollup = runner.run("order_completion_summary", {})
    grand_total = next(r for r in rollup if r["product_name"] == "ALL" and r["status"] == "ALL")
    assert grand_total["orders"] == 6 and grand_total["planned_units"] == 720

    review = runner.run(
        "batches_requiring_review", {**WINDOW, "threshold": 0.10, "machine_id": None}
    )
    assert review and all(r["machine_code"] == "CNC-03" for r in review)
    assert all(r["already_under_investigation"] == 0 for r in review)

    trend = runner.run("daily_production_trend", WINDOW)
    assert sum(t["units_produced"] for t in trend) == 720

    chart = runner.run(
        "characteristic_control_chart",
        {**WINDOW, "specification_id": _diameter_spec_id(client, engineer), "machine_id": None},
    )
    assert len(chart) == 8 and chart[-1]["mean_value"] > chart[-1]["ucl"]

    onset = runner.run("investigation.defect_onset", {**WINDOW, "machine_id": cnc3})
    assert onset[0]["previous_bucket_rate"] is None and onset[-1]["cumulative_rate"] > 0
    first_bad = next(o for o in onset if o["defect_rate"] >= 0.10)
    before = runner.run(
        "investigation.machine_events_before_onset",
        {
            "machine_id": cnc3,
            "onset_time": datetime.fromisoformat(first_bad["bucket_start"]),
            "lookback_hours": 6,
        },
    )
    assert before[0]["event_type"] == "TOOL_WEAR" and before[0]["minutes_before_onset"] >= 0
    lots = runner.run(
        "investigation.shared_material_lots", {"batch_ids": [r["batch_id"] for r in review]}
    )
    assert lots and lots[0]["affected_batches_using_lot"] >= 1


def test_control_chart_subgroups_cover_every_inspection_of_the_specification(
    db_session: Session,
    client: TestClient,
    engineer: dict[str, str],
    ids: Ids,
    simulated: dict[str, object],
) -> None:
    spec_id = _diameter_spec_id(client, engineer)
    rows = SqlQueryRunner(db_session).run(
        "characteristic_control_chart",
        {**WINDOW, "specification_id": spec_id, "machine_id": None},
    )
    assert rows and all(list(r) == CONTROL_CHART_COLUMNS for r in rows)

    inspections = db_session.scalar(
        select(func.count(Inspection.id)).where(Inspection.specification_id == spec_id)
    )
    assert sum(r["sample_count"] for r in rows) == inspections
    assert all(r["machine_code"] == "CNC-03" and r["sample_count"] == 30 for r in rows)

    first = rows[0]
    assert first["lcl"] < first["grand_mean"] < first["ucl"]
    assert first["lower_spec_limit"] == 19.9 and first["upper_spec_limit"] == 20.1
    assert first["target_value"] == 20.0
    assert all(r["grand_mean"] == first["grand_mean"] for r in rows)
    assert all((r["ucl"], r["lcl"]) == (first["ucl"], first["lcl"]) for r in rows), (
        "equal sample counts share the same limits"
    )
    assert all(r["min_value"] <= r["mean_value"] <= r["max_value"] for r in rows)
    assert all(r["std_dev"] is not None and r["std_dev"] > 0 for r in rows)

    keys = [(r["subgroup_start"], r["batch_id"]) for r in rows]
    assert keys == sorted(keys)
    assert rows[-1]["mean_value"] > rows[-1]["ucl"], "tool wear drifts the last batch above UCL"


def test_control_chart_limits_widen_for_smaller_subgroups(
    db_session: Session,
    client: TestClient,
    engineer: dict[str, str],
    simulated: dict[str, object],
) -> None:
    """A window that cuts the second batch in half gives that subgroup its own, wider limits."""
    rows = SqlQueryRunner(db_session).run(
        "characteristic_control_chart",
        {
            "window_start": datetime(2026, 11, 2, 6),
            "window_end": datetime(2026, 11, 2, 6, 45),
            "specification_id": _diameter_spec_id(client, engineer),
            "machine_id": None,
        },
    )
    assert [r["sample_count"] for r in rows] == [30, 14]
    full, partial = rows
    assert full["grand_mean"] == partial["grand_mean"]
    assert partial["ucl"] > full["ucl"] and partial["lcl"] < full["lcl"]

    def three_sigma(row: dict[str, object]) -> float:
        return (float(row["ucl"]) - float(row["grand_mean"])) * sqrt(int(row["sample_count"]))

    assert abs(three_sigma(full) - three_sigma(partial)) < 1e-3
    for row in rows:
        above = float(row["ucl"]) - float(row["grand_mean"])
        below = float(row["grand_mean"]) - float(row["lcl"])
        assert abs(above - below) <= 2e-4, "limits are symmetric up to the 4-place rounding"


def test_control_chart_machine_filter_follows_the_optional_parameter_pattern(
    db_session: Session,
    client: TestClient,
    engineer: dict[str, str],
    ids: Ids,
    simulated: dict[str, object],
) -> None:
    spec_id = _diameter_spec_id(client, engineer)
    runner = SqlQueryRunner(db_session)
    params = {**WINDOW, "specification_id": spec_id}
    everyone = runner.run("characteristic_control_chart", {**params, "machine_id": None})
    cnc3 = runner.run(
        "characteristic_control_chart", {**params, "machine_id": ids["machines"]["CNC-03"]}
    )
    cnc1 = runner.run(
        "characteristic_control_chart", {**params, "machine_id": ids["machines"]["CNC-01"]}
    )
    assert cnc3 == everyone and cnc1 == []

    one_batch = runner.run(
        "characteristic_control_chart",
        {
            "specification_id": spec_id,
            "window_start": datetime(2026, 11, 2, 6, 0),
            "window_end": datetime(2026, 11, 2, 6, 30),
            "machine_id": None,
        },
    )
    assert len(one_batch) == 1
    assert one_batch[0]["ucl"] is not None
    assert one_batch[0]["grand_mean"] == one_batch[0]["mean_value"]
