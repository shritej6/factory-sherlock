# ADR-0005: Rule-based investigation engine before any machine learning

## Status

Accepted. Recorded 2026-11-03. Implemented in `backend/app/investigation/`. Amended by [ADR-0009](ADR-0009-cusum-onset-rule.md), which adds a seventh rule (R7, CUSUM onset detection) within the same design; the six rules listed below are unchanged.

## Context

The defining feature of Factory Sherlock is explaining why quality deteriorated. There was a temptation to frame this as anomaly detection or root-cause prediction with a learned model. The project, however, runs on simulated data with known injected faults, is graded on database work, and is used by engineers who must be able to check every claim. A finding that cannot be traced to a query and its rows has no value here.

## Decision

Implement the investigation engine as an ordered set of deterministic, SQL-backed rules and defer any statistical or learned component:

- Six rules in `backend/app/investigation/rules.py`, run in a fixed order by `engine.investigate`:
  - R1 machine defect-rate comparison against the fleet (query 01),
  - R2 dominant defect category (query 03),
  - R3 time of quality deterioration, the first hourly bucket at or above the review threshold (`investigation.defect_onset`),
  - R4 machine events in the hours before the onset (`investigation.machine_events_before_onset`),
  - R5 batches at or above the review threshold that are not quarantined (query 08),
  - R6 material lots shared by the affected batches (`investigation.shared_material_lots`).
- Rules share a mutable `InvestigationContext`; later rules build on earlier results (R4 needs R3's onset, R6 needs R5's batch ids) and return `None` when their preconditions are not met.
- Thresholds are plain data in `RuleThresholds` (elevated rate at least 5 percent and twice the fleet rate; batch review rate 10 percent; six-hour event lookback; three-hour before-and-after comparison window) so they can be shown in documentation and tuned in one place.
- Each finding is an `Evidence` card with the rule code, title, narrative, query name, full SQL text, and result rows; the service persists cards in sequence and links flagged batches through `investigation_batches`.
- Wording discipline: narratives describe associations in time ("preceded", "after") and explicitly say that timing does not establish a cause. The engineer writes the conclusion when closing the investigation; both the generated summary and the human conclusion are stored.

## Consequences

Positive:

- Every finding is reproducible: open the SQL on the evidence card, bind the same parameters, and the rows match.
- The engine is unit-testable without MySQL by passing a fake `QueryRunner`.
- Behaviour is predictable for demonstrations: the injected `TOOL_WEAR` fault in `demo_scenario.json` produces an R3 onset, an R4 event, and R5 batches on `CNC-03`.
- The rules reuse the same query files the dashboards use, so numbers agree across screens.

Negative or accepted costs:

- Rules only find what they were written to find. A fault pattern outside the six rules (for example a defect that correlates with a supplier but not a lot) produces no evidence card.
- Thresholds are fixed constants; they are not learned from history and may need tuning for different simulation parameters.
- Rules are sequential and synchronous within the request; six queries run per investigation. Acceptable at current data volumes.
- `product_id` is accepted and stored on an investigation but no rule currently filters by product; the scope is machine and time window.

## Alternatives considered

- Statistical process control (control charts, CUSUM) on measurements. A reasonable next step; deferred because it needs calibrated limits per characteristic and would still require the rule layer to turn signals into evidence.
- Supervised root-cause classification trained on simulated faults. Rejected for now: the model would learn the simulator's fault signatures rather than real behaviour, and its outputs could not be shown as SQL evidence.
- Large language model summarisation of raw data. Rejected: non-deterministic output cannot be stored as reproducible evidence, and the project requires that conclusions be auditable.
- A single large SQL query producing all findings. Rejected: later rules depend on earlier results (onset time, batch ids), and separate cards are easier to read and test.
