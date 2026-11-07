"""Rules are exercised with a fake query runner so no database is needed."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import pytest
from app.investigation.engine import investigate
from app.investigation.rules import (
    InvestigationContext,
    RuleThresholds,
    hours_apart,
    rule_cusum_onset,
)

WINDOW = (datetime(2026, 11, 2), datetime(2026, 11, 4))
CAUSAL_WORDS = ("caused", "because", "due to", "proves", "resulted in")


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
        "investigation.hourly_defect_rates": hourly_rows([0, 0, 0, 5, 10]),
    }


def hourly_rows(failed_per_hour: list[int], inspected: int = 20) -> list[dict[str, Any]]:
    """Hourly buckets from 06:00 with the given failure counts, like the SQL returns them."""
    return [
        {
            "bucket_start": f"2026-11-02T{6 + hour:02d}:00:00",
            "inspected_count": inspected,
            "failed_count": failed,
            "defect_rate": round(failed / inspected, 4),
        }
        for hour, failed in enumerate(failed_per_hour)
    ]


def test_elevated_machine_produces_seven_evidence_cards_and_flags_batches() -> None:
    runner = FakeRunner(elevated_dataset())
    ctx = InvestigationContext(
        machine_id=3, machine_code="CNC-03", window_start=WINDOW[0], window_end=WINDOW[1]
    )
    report = investigate(ctx, runner)
    assert [e.rule_code for e in report.evidence] == ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    assert report.elevated is True
    assert report.affected_batch_ids == [11, 12]
    assert "elevated defect rate of 20.0%" in report.summary
    assert "Oversized diameter" in report.summary
    assert "does not establish" in report.summary  # correlation is not causation
    assert "L201" in report.summary and "L202" not in report.summary
    # R3 onset is 09:00 (rate 0.25); the CUSUM reaches 0.225 >= 0.10 in that same hour.
    assert report.evidence[6].rows[3] == {
        "bucket_start": "2026-11-02T09:00:00",
        "inspected_count": 20,
        "failed_count": 5,
        "defect_rate": 0.25,
        "cusum": 0.225,
        "signal": True,
    }
    assert "The CUSUM onset estimate falls in the same hour." in report.summary
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
    assert [e.rule_code for e in report.evidence] == ["R1", "R2", "R3", "R4", "R5", "R7"]


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
    assert "R3" not in codes and "R4" not in codes and "R7" not in codes
    assert "CNC-03 had the highest defect rate" in report.evidence[0].narrative


def machine_ctx(onset_time: datetime | None = None) -> InvestigationContext:
    ctx = InvestigationContext(
        machine_id=3, machine_code="CNC-03", window_start=WINDOW[0], window_end=WINDOW[1]
    )
    ctx.onset_time = onset_time
    return ctx


def run_cusum(rows: list[dict[str, Any]], onset_time: datetime | None = None) -> tuple[Any, Any]:
    ctx = machine_ctx(onset_time)
    card = rule_cusum_onset(ctx, FakeRunner({"investigation.hourly_defect_rates": rows}))
    return ctx, card


def test_cusum_allowance_is_half_the_elevated_rate() -> None:
    assert RuleThresholds().cusum_allowance == 0.025


def test_cusum_signals_on_a_step_change_in_the_defect_rate() -> None:
    ctx, card = run_cusum(hourly_rows([0, 0, 0, 0, 4, 4, 4]))
    assert card is not None and card.rule_code == "R7"
    assert card.query_name == "investigation.hourly_defect_rates"
    assert [r["signal"] for r in card.rows] == [False, False, False, False, True, True, True]
    assert ctx.cusum_onset_time == datetime(2026, 11, 2, 10)
    assert "first reached 0.1750 in the hour starting 2026-11-02T10:00:00" in card.narrative
    assert "while R3 found no single hour at or above 10.0%" in card.narrative


def test_cusum_does_not_signal_on_flat_noise() -> None:
    ctx, card = run_cusum(hourly_rows([0, 1, 0, 1, 1, 0], inspected=40))
    assert card is not None
    assert all(r["cusum"] == 0.0 and r["signal"] is False for r in card.rows)
    assert ctx.cusum_onset_time is None
    assert "stayed below the decision interval in every hour" in card.narrative


def test_cusum_returns_none_without_a_machine_or_with_too_few_hours() -> None:
    _, card = run_cusum(hourly_rows([0, 10]))
    assert card is None
    fleet = InvestigationContext(
        machine_id=None, machine_code=None, window_start=WINDOW[0], window_end=WINDOW[1]
    )
    runner = FakeRunner({"investigation.hourly_defect_rates": hourly_rows([0, 0, 0, 5])})
    assert rule_cusum_onset(fleet, runner) is None
    assert runner.calls == []


def test_cusum_arithmetic_matches_a_hand_computed_example() -> None:
    # p0 = (2 + 4 + 0) / 300 = 0.02, k = 0.025, so each hour adds rate - 0.045:
    # 0.02 -> 0, 0.04 -> 0, 0.00 -> 0, 0.10 -> 0.055, 0.20 -> 0.055 + 0.155 = 0.21.
    _, card = run_cusum(hourly_rows([2, 4, 0, 10, 20], inspected=100))
    assert card is not None
    assert [r["cusum"] for r in card.rows] == [0.0, 0.0, 0.0, 0.055, 0.21]
    assert [r["signal"] for r in card.rows] == [False, False, False, False, True]
    assert list(card.rows[0]) == [
        "bucket_start",
        "inspected_count",
        "failed_count",
        "defect_rate",
        "cusum",
        "signal",
    ]
    assert "reference 2.0% from the first 3 hours" in card.narrative


@pytest.mark.parametrize(
    ("later", "earlier", "expected"),
    [
        (datetime(2026, 11, 2, 9, 30), datetime(2026, 11, 2, 9, 0), None),
        (datetime(2026, 11, 2, 10, 0), datetime(2026, 11, 2, 9, 0), "1 hour after"),
        (datetime(2026, 11, 2, 12, 0), datetime(2026, 11, 2, 9, 0), "3 hours after"),
        (datetime(2026, 11, 2, 7, 0), datetime(2026, 11, 2, 9, 0), "2 hours before"),
    ],
)
def test_hours_apart_counts_whole_hours_in_either_direction(
    later: datetime, earlier: datetime, expected: str | None
) -> None:
    assert hours_apart(later, earlier, after="after", before="before") == expected


def test_cusum_narrative_compares_with_the_r3_onset() -> None:
    _, later = run_cusum(hourly_rows([0, 0, 0, 0, 4, 4]), onset_time=datetime(2026, 11, 2, 9))
    assert later is not None
    assert "1 hour after the first hour at or above 10.0% found by R3 (09:00)" in later.narrative
    _, same = run_cusum(hourly_rows([0, 0, 0, 0, 4, 4]), onset_time=datetime(2026, 11, 2, 10))
    assert same is not None and "the same hour as the first hour" in same.narrative
    _, quiet = run_cusum(hourly_rows([0, 0, 0, 1, 0, 0]), onset_time=datetime(2026, 11, 2, 9))
    assert quiet is not None
    assert "R3 found an hour at or above 10.0% starting 09:00, but" in quiet.narrative


@pytest.mark.parametrize(
    "failed_per_hour", [[0, 0, 0, 0, 4, 4, 4], [0, 1, 0, 1, 1, 0], [2, 4, 0, 10, 20]]
)
def test_cusum_narrative_never_uses_causal_language(failed_per_hour: list[int]) -> None:
    for onset in (None, datetime(2026, 11, 2, 9)):
        _, card = run_cusum(hourly_rows(failed_per_hour, inspected=100), onset_time=onset)
        assert card is not None
        lowered = card.narrative.lower()
        assert "caused" not in lowered and "because" not in lowered


def _cnc3_context() -> InvestigationContext:
    return InvestigationContext(
        machine_id=3, machine_code="CNC-03", window_start=WINDOW[0], window_end=WINDOW[1]
    )


@pytest.mark.parametrize(
    ("rate", "fleet", "elevated"),
    [
        (0.05, 0.025, True),  # exactly the minimum rate and exactly twice the fleet
        (0.0499, 0.01, False),  # below the minimum rate although far above the fleet
        (0.05, 0.0251, False),  # at the minimum rate but less than twice the fleet
        (0.05, 0.0, True),  # a zero fleet rate counts as elevated at the minimum
        (0.5, 0.3, False),  # high in absolute terms but in line with the fleet
    ],
)
def test_elevation_threshold_boundaries(rate: float, fleet: float, elevated: bool) -> None:
    data = elevated_dataset()
    for row in data["machine_defect_rate_comparison"]:
        row["fleet_defect_rate"] = fleet
    data["machine_defect_rate_comparison"][0]["defect_rate"] = rate
    ctx = _cnc3_context()
    investigate(ctx, FakeRunner(data))
    assert ctx.elevated is elevated


def test_onset_is_the_first_bucket_at_or_above_ten_percent() -> None:
    data = elevated_dataset()
    buckets = [("08", 0.0999, None), ("09", 0.1, 0.0999), ("10", 0.4, 0.1)]
    data["investigation.defect_onset"] = [
        {
            "bucket_start": f"2026-11-02T{hour}:00:00",
            "inspected": 20,
            "failed": int(rate * 20),
            "defect_rate": rate,
            "previous_bucket_rate": previous,
            "cumulative_rate": rate,
        }
        for hour, rate, previous in buckets
    ]
    runner = FakeRunner(data)
    ctx = _cnc3_context()
    investigate(ctx, runner)
    assert ctx.onset_time == datetime(2026, 11, 2, 9)
    calls = dict(runner.calls)
    assert calls["investigation.machine_events_before_onset"] == {
        "machine_id": 3,
        "onset_time": datetime(2026, 11, 2, 9),
        "lookback_hours": 6,
    }
    assert calls["batches_requiring_review"]["threshold"] == 0.10
    assert calls["batches_requiring_review"]["machine_id"] == 3


def test_no_onset_skips_the_event_rule_and_says_so() -> None:
    data = elevated_dataset()
    for row in data["investigation.defect_onset"]:
        row["defect_rate"] = 0.05
    report = investigate(_cnc3_context(), FakeRunner(data))
    codes = [e.rule_code for e in report.evidence]
    assert "R3" in codes and "R4" not in codes
    r3 = next(e for e in report.evidence if e.rule_code == "R3")
    assert "never reached 10.0%" in r3.narrative


def test_narratives_and_summary_never_assert_causation() -> None:
    report = investigate(_cnc3_context(), FakeRunner(elevated_dataset()))
    for sentence in [report.summary, *(e.narrative for e in report.evidence)]:
        lowered = sentence.lower()
        assert not any(word in lowered for word in CAUSAL_WORDS), sentence
    r4 = next(e for e in report.evidence if e.rule_code == "R4")
    assert "does not prove a cause" in r4.narrative
    assert "does not establish one" in report.summary
