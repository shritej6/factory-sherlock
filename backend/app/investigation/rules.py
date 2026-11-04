"""Investigation rules.

Each rule takes an ``InvestigationContext`` and a ``QueryRunner`` and returns
an ``Evidence`` card, or ``None`` when the rule has nothing to say. Rules only
read; persistence is the service's job. Thresholds live in ``RuleThresholds``
so they can be tuned in one place and shown in documentation.

Wording discipline: rules describe associations in time ("after", "during")
and never state that an event caused a defect. Causal judgement is left to
the engineer who closes the investigation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.repositories.query_runner import QueryRunner


@dataclass(frozen=True)
class RuleThresholds:
    # A machine is "elevated" when its rate is at least this absolute value and
    # at least this multiple of the fleet rate.
    elevated_min_rate: float = 0.05
    elevated_fleet_multiple: float = 2.0
    # A batch is affected when its defect rate reaches this value.
    batch_review_rate: float = 0.10
    # Hours to look back from the onset bucket for machine events.
    event_lookback_hours: int = 6


@dataclass
class InvestigationContext:
    machine_id: int | None
    machine_code: str | None
    window_start: datetime
    window_end: datetime
    thresholds: RuleThresholds = field(default_factory=RuleThresholds)
    # Filled progressively as rules run so later rules can build on earlier ones.
    elevated: bool = False
    machine_rate: float | None = None
    fleet_rate: float | None = None
    dominant_defect: str | None = None
    onset_time: datetime | None = None
    affected_batch_ids: list[int] = field(default_factory=list)
    affected_batch_numbers: list[str] = field(default_factory=list)
    related_events: list[dict[str, Any]] = field(default_factory=list)
    shared_lots: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Evidence:
    rule_code: str
    title: str
    narrative: str
    query_name: str
    query_sql: str
    rows: list[dict[str, Any]]


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def rule_defect_rate_elevation(ctx: InvestigationContext, runner: QueryRunner) -> Evidence | None:
    """R1: compare the machine's defect rate with the fleet over the window."""
    name = "machine_defect_rate_comparison"
    rows = runner.run(name, {"window_start": ctx.window_start, "window_end": ctx.window_end})
    if ctx.machine_id is None:
        worst = next((r for r in rows if r["inspected"] and r["defect_rank"] == 1), None)
        if worst is not None:
            ctx.machine_rate = worst["fleet_defect_rate"] or 0.0
            ctx.fleet_rate = ctx.machine_rate
        narrative = (
            "No machine inspections fall inside the window."
            if worst is None
            else f"{worst['machine_code']} had the highest defect rate in the window "
            f"({_pct(worst['defect_rate'])} against a fleet rate of "
            f"{_pct(worst['fleet_defect_rate'])})."
        )
        return Evidence(
            "R1", "Machine defect-rate comparison", narrative, name, runner.sql(name), rows
        )

    mine = next((r for r in rows if r["machine_id"] == ctx.machine_id), None)
    if mine is None or not mine["inspected"]:
        narrative = f"{ctx.machine_code} has no inspections in the window."
        return Evidence(
            "R1", "Machine defect-rate comparison", narrative, name, runner.sql(name), rows
        )
    ctx.machine_rate = mine["defect_rate"] or 0.0
    ctx.fleet_rate = mine["fleet_defect_rate"] or 0.0
    t = ctx.thresholds
    ctx.elevated = ctx.machine_rate >= t.elevated_min_rate and (
        ctx.fleet_rate == 0 or ctx.machine_rate >= t.elevated_fleet_multiple * ctx.fleet_rate
    )
    comparison = "elevated relative to" if ctx.elevated else "in line with"
    narrative = (
        f"{ctx.machine_code} failed {mine['failed']} of {mine['inspected']} inspections "
        f"({_pct(ctx.machine_rate)}), rank {mine['defect_rank']} of {len(rows)} machines. "
        f"This is {comparison} the fleet rate of {_pct(ctx.fleet_rate)} "
        f"(threshold: at least {_pct(t.elevated_min_rate)} and "
        f"{t.elevated_fleet_multiple:g} times the fleet rate)."
    )
    return Evidence("R1", "Machine defect-rate comparison", narrative, name, runner.sql(name), rows)


def rule_dominant_defect(ctx: InvestigationContext, runner: QueryRunner) -> Evidence | None:
    """R2: which defect category dominates on the machine."""
    name = "recurring_defects"
    rows = runner.run(
        name,
        {
            "window_start": ctx.window_start,
            "window_end": ctx.window_end,
            "machine_id": ctx.machine_id,
        },
    )
    if not rows:
        return None
    if ctx.machine_id is None:
        totals: dict[str, int] = {}
        for row in rows:
            totals[row["defect_name"]] = totals.get(row["defect_name"], 0) + int(row["occurrences"])
        ctx.dominant_defect = max(totals, key=lambda k: totals[k])
        narrative = (
            f"{ctx.dominant_defect} was the most frequent defect across the fleet: "
            f"{totals[ctx.dominant_defect]} of {sum(totals.values())} recorded defects."
        )
        return Evidence("R2", "Dominant defect category", narrative, name, runner.sql(name), rows)
    top = rows[0]
    ctx.dominant_defect = top["defect_name"]
    narrative = (
        f"{top['defect_name']} was the most frequent defect on {top['machine_code']}: "
        f"{top['occurrences']} of {top['machine_total']} recorded defects "
        f"({_pct(top['share_of_machine_defects'])})."
    )
    return Evidence("R2", "Dominant defect category", narrative, name, runner.sql(name), rows)


def rule_defect_onset(ctx: InvestigationContext, runner: QueryRunner) -> Evidence | None:
    """R3: find the first hour at which the defect rate crossed the review threshold."""
    if ctx.machine_id is None:
        return None
    name = "investigation.defect_onset"
    rows = runner.run(
        name,
        {
            "machine_id": ctx.machine_id,
            "window_start": ctx.window_start,
            "window_end": ctx.window_end,
        },
    )
    onset = next(
        (r for r in rows if (r["defect_rate"] or 0) >= ctx.thresholds.batch_review_rate), None
    )
    if onset is None:
        narrative = (
            f"The hourly defect rate never reached {_pct(ctx.thresholds.batch_review_rate)} "
            "inside the window."
        )
    else:
        ctx.onset_time = datetime.fromisoformat(onset["bucket_start"])
        narrative = (
            f"The hourly defect rate first reached {_pct(onset['defect_rate'])} in the hour "
            f"starting {onset['bucket_start']} "
            f"(previous non-empty hour: {_pct(onset['previous_bucket_rate'])})."
        )
    return Evidence("R3", "Time of quality deterioration", narrative, name, runner.sql(name), rows)


def rule_related_machine_events(ctx: InvestigationContext, runner: QueryRunner) -> Evidence | None:
    """R4: list machine events shortly before the onset (association, not causation)."""
    if ctx.machine_id is None or ctx.onset_time is None:
        return None
    name = "investigation.machine_events_before_onset"
    rows = runner.run(
        name,
        {
            "machine_id": ctx.machine_id,
            "onset_time": ctx.onset_time,
            "lookback_hours": ctx.thresholds.event_lookback_hours,
        },
    )
    ctx.related_events = rows
    if not rows:
        narrative = (
            f"No fault or maintenance events were recorded on {ctx.machine_code} in the "
            f"{ctx.thresholds.event_lookback_hours} hours before the onset."
        )
    else:
        first = rows[0]
        narrative = (
            f"{len(rows)} event(s) preceded the onset. The most recent was "
            f"{first['event_type']} ({first['description']}) "
            f"{first['minutes_before_onset']} minutes before the defect rate rose. "
            "Timing suggests a relationship worth checking; it does not prove a cause."
        )
    return Evidence("R4", "Machine events before onset", narrative, name, runner.sql(name), rows)


def rule_affected_batches(ctx: InvestigationContext, runner: QueryRunner) -> Evidence | None:
    """R5: batches above the review threshold that are not yet quarantined."""
    name = "batches_requiring_review"
    rows = runner.run(
        name,
        {
            "window_start": ctx.window_start,
            "window_end": ctx.window_end,
            "threshold": ctx.thresholds.batch_review_rate,
            "machine_id": ctx.machine_id,
        },
    )
    ctx.affected_batch_ids = [r["batch_id"] for r in rows]
    ctx.affected_batch_numbers = [r["batch_number"] for r in rows]
    scope = ctx.machine_code or "all machines"
    narrative = (
        f"{len(rows)} batch(es) on {scope} reached a defect rate of "
        f"{_pct(ctx.thresholds.batch_review_rate)} or more and are not quarantined."
        + (f" Worst: {rows[0]['batch_number']} at {_pct(rows[0]['defect_rate'])}." if rows else "")
    )
    return Evidence("R5", "Batches requiring review", narrative, name, runner.sql(name), rows)


def rule_shared_material_lots(ctx: InvestigationContext, runner: QueryRunner) -> Evidence | None:
    """R6: material lots consumed by the affected batches."""
    if not ctx.affected_batch_ids:
        return None
    name = "investigation.shared_material_lots"
    rows = runner.run(name, {"batch_ids": ctx.affected_batch_ids})
    shared = [r for r in rows if r["affected_batches_using_lot"] > 1]
    ctx.shared_lots = [r["lot_number"] for r in shared]
    if shared:
        listed = ", ".join(
            f"{r['lot_number']} ({r['affected_batches_using_lot']} of "
            f"{r['total_batches_using_lot']} batches)"
            for r in shared
        )
        narrative = f"Affected batches share material lot(s): {listed}."
    else:
        narrative = "The affected batches do not share a material lot."
    return Evidence("R6", "Shared material lots", narrative, name, runner.sql(name), rows)


RULES = (
    rule_defect_rate_elevation,
    rule_dominant_defect,
    rule_defect_onset,
    rule_related_machine_events,
    rule_affected_batches,
    rule_shared_material_lots,
)
