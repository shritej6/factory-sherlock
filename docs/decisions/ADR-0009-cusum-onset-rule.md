# ADR-0009: CUSUM onset detection as a seventh rule, not a model

## Status

Accepted. Recorded 2026-11-07. Implemented in `backend/app/investigation/rules.py` (`rule_cusum_onset`, R7) and `database/queries/investigation/hourly_defect_rates.sql`. Amends [ADR-0005](ADR-0005-rule-based-investigation-before-ml.md) by adding one rule; it does not change the six existing rules or the design they follow.

## Context

Rule R3 dates the onset of a quality problem as the first hourly bucket whose defect rate reaches the batch review threshold (0.10). This is easy to explain and to check, but it is a single-hour test: one bad hour flags an onset, and a gradual rise that stays just under the threshold for several hours is never dated at all. ADR-0005 listed statistical process control (control charts, CUSUM) as the reasonable next step and deferred it because it would need calibrated limits per characteristic.

The development roadmap asked for a second, statistical onset estimate that could be placed beside R3 so that an engineer sees whether two different methods agree. The constraints from ADR-0005 still hold: no learned model, no new dependency, every finding backed by SQL and rows the engineer can rerun, association language only. The platform is graded as database work and demonstrated on the seed 42 scenario (`TOOL_WEAR` on CNC-03 from 08:00), so the rule has to signal on CNC-03 and stay quiet on CNC-01 and CNC-02 with constants that can be written down and defended.

## Decision

Add rule R7, a one-sided upper CUSUM over hourly defect rates, as the last entry of `RULES`:

- Query: `investigation.hourly_defect_rates` returns one row per hourly bucket with `inspected_count`, `failed_count`, `defect_rate`, bucketed and windowed exactly like `defect_onset`. Hours with no inspections are absent. A separate file is used rather than reusing `defect_onset.sql`: the card then shows exactly the columns the formula consumes, R7 does not inherit the LAG and cumulative columns it does not read, and a later change to R3's query cannot silently change R7.
- Formula: `S_0 = 0`, `S_t = max(0, S_{t-1} + (p_t - p0 - k))`, signal when `S_t >= h`, with the statistic rounded to four places at every step so that the stored value is the value used for the decision.
- Reference `p0`: the machine's own pooled defect rate over its first `cusum_baseline_hours` (3) hourly rows in the window. The fleet rate from R1 was considered and rejected as the reference: it includes the machine under investigation (3.6 percent in the demo against about 0.4 percent on the healthy machines), it is unavailable when R1 found no inspections, and the question R7 answers is when this machine departed from its own earlier behaviour.
- Allowance `k`: `elevated_min_rate / 2` = 0.025, exposed as the `RuleThresholds.cusum_allowance` property. Hours less than 2.5 points above the reference add nothing, which is what keeps single noisy hours (one failure in eighty inspections is 1.25 points) from accumulating.
- Decision interval `h`: `cusum_decision_interval` = 0.10. One hour needs a rate of `p0 + 0.125` to signal on its own; a run of hours a few points above the reference signals after the excess sums to ten points. On the demo scenario CNC-03 reaches 0.1375 at 10:00 and signals; CNC-01 and CNC-02 stay at zero throughout.
- Rows: the query rows plus two derived columns, `cusum` and `signal`. This is the first rule whose stored rows are not the bare query result, and the deviation is deliberate: the arithmetic is a stated formula over values in the same row and the row before it, so a reviewer can recompute it by hand, which is the same standard of checkability the SQL meets.
- Context and summary: R7 writes `cusum_onset_time`; `build_summary` adds one neutral sentence when both R3 and R7 produced an onset, stating that the estimates fall in the same hour or how many hours apart they are. The narrative compares the signalling hour with R3's onset in association language ("the same hour as", "one hour after") and ends with "it does not identify what changed".
- Preconditions: the rule returns `None` for fleet-wide investigations and when fewer than three hourly rows exist, because the reference cannot be estimated.

## Consequences

Positive:

- Two independent onset estimates sit side by side on the case board. Agreement strengthens the engineer's confidence in the dating; disagreement is reported neutrally and points at the hours worth looking at.
- A gradual rise that never crosses 0.10 in any single hour can still be dated, because the statistic accumulates.
- Nothing in ADR-0005 is weakened: no model, no new dependency, deterministic output, constants in `RuleThresholds`, SQL and rows stored on the card, unit tests with a fake runner and an API test on the simulated scenario.

Negative or accepted costs:

- The reference is estimated from the first three hours of the window. If the fault is already present at the window start, the baseline absorbs it and R7 does not signal; the engineer has to widen the window backwards. R3 does not have this weakness, which is one reason both rules are kept.
- The statistic treats every hourly row alike regardless of how many inspections it holds. A two-inspection bucket at the end of a shift can move it a lot; the `inspected_count` column on the same row makes this visible but the rule does not weight for it.
- `h` and `k` are tuned against the simulator's fault model, as every threshold in `RuleThresholds` is; different production rates or fault shapes may need different values.
- A seventh query runs per investigation, over the same tables and indexes as R3; the cost is one more grouped scan over the machine's inspections in the window.

## Alternatives considered

- Reusing `defect_onset.sql` for R7. Rejected: the card would show LAG and cumulative columns the formula does not use, and the two rules would be coupled through one file's result shape.
- Computing the CUSUM in SQL with a recursive CTE or window functions. Rejected: the `max(0, ...)` reset makes the statistic non-linear, so it cannot be written as a windowed `SUM`; a recursive CTE would work but would spread the constants across SQL and Python and make the card's SQL harder to read.
- Using the fleet rate from R1 as `p0`. Rejected for the reasons given under Decision.
- A two-sided CUSUM, also detecting improvement. Deferred: investigations are opened on deteriorating quality, and a downward signal would need its own narrative and tests.
- A control chart on measurement values per characteristic (the option named in ADR-0005). Still deferred: it needs limits per specification and a different data path (measurements rather than pass or fail counts); the hourly rate CUSUM reuses the inspection results every other rule already works on.
