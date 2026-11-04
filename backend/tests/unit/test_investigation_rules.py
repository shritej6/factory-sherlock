"""Rules are exercised with a fake query runner so no database is needed."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.investigation.engine import investigate
from app.investigation.rules import InvestigationContext

WINDOW = (datetime(2026, 11, 2), datetime(2026, 11, 4))


class FakeRunner:
    def __init__(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.data = data
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, name: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        self.calls.append((name, dict(params)))
        return self.data.get(name, [])

    def sql(self, name: str) -> str:
        return f"-- {name}\nSELECT 1;"


def elevated_dataset() -> dict[str, list[dict[str, Any]]]:
    return {
        "machine_defect_rate_comparison": [
            {
                "machine_id": 3,
                "machine_code": "CNC-03",
                "inspected": 100,
                "failed": 20,
                "defect_rate": 0.2,
                "fleet_defect_rate": 0.08,
                "defect_rank": 1,
            },
            {
                "machine_id": 1,
                "machine_code": "CNC-01",
                "inspected": 100,
                "failed": 2,
                "defect_rate": 0.02,
                "fleet_defect_rate": 0.08,
                "defect_rank": 2,
            },
        ],
        "recurring_defects": [
            {
                "machine_code": "CNC-03",
                "defect_code": "OVERSIZE_DIAMETER",
                "defect_name": "Oversized diameter",
                "occurrences": 18,
                "machine_total": 20,
                "share_of_machine_defects": 0.9,
                "rank_within_machine": 1,
            }
        ],
        "investigation.defect_onset": [
            {
                "bucket_start": "2026-11-02T08:00:00",
                "inspected": 20,
                "failed": 0,
                "defect_rate": 0.0,
                "previous_bucket_rate": None,
                "cumulative_rate": 0.0,
            },
            {
                "bucket_start": "2026-11-02T09:00:00",
                "inspected": 20,
                "failed": 5,
                "defect_rate": 0.25,
                "previous_bucket_rate": 0.0,
                "cumulative_rate": 0.125,
            },
        ],
        "investigation.machine_events_before_onset": [
            {
                "event_id": 9,
                "event_type": "TOOL_WEAR",
                "severity": "WARNING",
                "description": "tool wear",
                "occurred_at": "2026-11-02 08:30:00",
                "minutes_before_onset": 30,
            }
        ],
        "batches_requiring_review": [
            {"batch_id": 11, "batch_number": "B-11", "defect_rate": 0.3, "machine_code": "CNC-03"},
            {"batch_id": 12, "batch_number": "B-12", "defect_rate": 0.2, "machine_code": "CNC-03"},
        ],
        "investigation.shared_material_lots": [
            {"lot_number": "L201", "affected_batches_using_lot": 2, "total_batches_using_lot": 5},
            {"lot_number": "L202", "affected_batches_using_lot": 1, "total_batches_using_lot": 3},
        ],
    }


def test_elevated_machine_produces_six_evidence_cards_and_flags_batches() -> None:
    runner = FakeRunner(elevated_dataset())
    ctx = InvestigationContext(
        machine_id=3, machine_code="CNC-03", window_start=WINDOW[0], window_end=WINDOW[1]
    )
    report = investigate(ctx, runner)
    assert [e.rule_code for e in report.evidence] == ["R1", "R2", "R3", "R4", "R5", "R6"]
    assert report.elevated is True
    assert report.affected_batch_ids == [11, 12]
    assert "elevated defect rate of 20.0%" in report.summary
    assert "Oversized diameter" in report.summary
    assert "does not establish" in report.summary  # correlation is not causation
    assert "L201" in report.summary and "L202" not in report.summary
    # Every evidence card carries the SQL it was built from.
    assert all(e.query_sql.startswith("--") for e in report.evidence)
    # R6 receives the batch ids found by R5.
    shared_call = next(c for c in runner.calls if c[0] == "investigation.shared_material_lots")
    assert shared_call[1] == {"batch_ids": [11, 12]}


def test_machine_in_line_with_fleet_is_not_elevated() -> None:
    data = elevated_dataset()
    data["machine_defect_rate_comparison"][0].update({"failed": 3, "defect_rate": 0.03})
    data["batches_requiring_review"] = []
    ctx = InvestigationContext(
        machine_id=3, machine_code="CNC-03", window_start=WINDOW[0], window_end=WINDOW[1]
    )
    report = investigate(ctx, FakeRunner(data))
    assert report.elevated is False
    assert report.affected_batch_ids == []
    assert "No action is indicated" in report.summary
    assert [e.rule_code for e in report.evidence] == ["R1", "R2", "R3", "R4", "R5"]


def test_no_data_gives_a_plain_summary() -> None:
    ctx = InvestigationContext(
        machine_id=3, machine_code="CNC-03", window_start=WINDOW[0], window_end=WINDOW[1]
    )
    report = investigate(ctx, FakeRunner({}))
    assert report.summary == "No inspection data was found for the selected scope."
    assert [e.rule_code for e in report.evidence] == ["R1", "R3", "R5"]


def test_fleet_wide_investigation_skips_machine_specific_rules() -> None:
    ctx = InvestigationContext(
        machine_id=None, machine_code=None, window_start=WINDOW[0], window_end=WINDOW[1]
    )
    report = investigate(ctx, FakeRunner(elevated_dataset()))
    codes = [e.rule_code for e in report.evidence]
    assert "R3" not in codes and "R4" not in codes
    assert "CNC-03 had the highest defect rate" in report.evidence[0].narrative
