"""Every documented SQL file runs against simulated data and returns sane shapes."""

from datetime import datetime

from app.repositories.query_runner import SqlQueryRunner
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

Ids = dict[str, dict[str, int]]
WINDOW = {"window_start": datetime(2026, 11, 1), "window_end": datetime(2026, 11, 5)}


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
