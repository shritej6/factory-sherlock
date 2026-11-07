"""Turns the investigation context into a short, careful written summary."""

from datetime import datetime

from app.investigation.rules import InvestigationContext, hours_apart


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _onset_agreement(threshold_onset: datetime, cusum_onset: datetime) -> str:
    """One neutral sentence on whether the two onset estimates coincide."""
    offset = hours_apart(cusum_onset, threshold_onset, after="later", before="earlier")
    if offset is None:
        return "The CUSUM onset estimate falls in the same hour."
    return (
        f"The CUSUM onset estimate ({cusum_onset:%H:%M}) is {offset} "
        "than the threshold-based onset."
    )


def build_summary(ctx: InvestigationContext) -> str:
    parts: list[str] = []
    scope = ctx.machine_code or "The fleet"
    if ctx.machine_rate is not None and ctx.machine_code is None:
        parts.append(
            f"The fleet recorded a defect rate of {_pct(ctx.machine_rate)} during the selected "
            "period; onset and event rules apply to single-machine investigations only."
        )
    elif ctx.machine_rate is not None:
        level = "an elevated" if ctx.elevated else "a"
        parts.append(
            f"{scope} recorded {level} defect rate of {_pct(ctx.machine_rate)} during the "
            f"selected period (fleet: {_pct(ctx.fleet_rate)})."
        )
    if ctx.dominant_defect:
        parts.append(f"{ctx.dominant_defect} was the most frequent defect.")
    if ctx.onset_time:
        parts.append(f"The increase began around {ctx.onset_time:%Y-%m-%d %H:%M}.")
    if ctx.onset_time and ctx.cusum_onset_time:
        parts.append(_onset_agreement(ctx.onset_time, ctx.cusum_onset_time))
    if ctx.related_events:
        event = ctx.related_events[0]
        minutes = int(event["minutes_before_onset"])
        when = (
            f"{minutes} minutes before the onset hour"
            if minutes >= 0
            else f"{-minutes} minutes into the onset hour"
        )
        parts.append(
            f"A {event['event_type']} event was recorded {when}; the timing is consistent "
            "with a relationship but does not establish one."
        )
    if ctx.affected_batch_numbers:
        shown = ", ".join(ctx.affected_batch_numbers[:5])
        more = len(ctx.affected_batch_numbers) - 5
        parts.append(
            f"{len(ctx.affected_batch_numbers)} batch(es) exceed the review threshold: {shown}"
            + (f" and {more} more." if more > 0 else ".")
        )
    if ctx.shared_lots:
        parts.append(f"They share material lot(s) {', '.join(ctx.shared_lots)}.")
    if ctx.elevated:
        parts.append(
            "Recommended: inspect the machine and tooling, review the listed batches, and "
            "decide whether to quarantine them."
        )
    elif ctx.machine_rate is not None:
        parts.append("No action is indicated by the rules; continue routine monitoring.")
    return " ".join(parts) if parts else "No inspection data was found for the selected scope."
