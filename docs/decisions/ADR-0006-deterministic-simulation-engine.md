# ADR-0006: Deterministic, persistence-free simulation engine

## Status

Accepted. Recorded 2026-11-03. Implemented in `backend/app/simulation/` and `backend/app/services/simulation_service.py`.

## Context

There is no physical factory. The platform needs production history that is realistic enough for traceability and investigation to be meaningful, large enough to exercise the queries, and reproducible enough that a demonstration, a test, and a grader's run all show the same picture. Injected faults must leave signatures that the investigation rules can find.

## Decision

Implement the virtual factory as a pure engine that is deterministic for a given input and knows nothing about persistence:

- Inputs are frozen dataclasses: `SimulationConfig` (seed, start time, batches per machine, units per batch, minutes per batch, batches per order, fault scenarios, alert defect rate) and `Catalog` (products with specifications and usable material lot ids, machines, defect type ids). `simulation_service.load_catalog` builds the catalog from MySQL.
- All randomness flows through one `random.Random(config.seed)` owned by `SimulationEngine`; `MeasurementGenerator` draws from it. The same `(config, catalog)` pair yields the same `SimulationOutput`.
- Measurements follow a normal distribution centred on the target with sigma equal to one third of the tolerance; faults distort this through `MeasurementEffect` (offset as a fraction of tolerance, sigma multiplier, gross-defect probability). Five fault kinds exist: `TOOL_WEAR` (drift on the primary characteristic), `CALIBRATION_DRIFT` (constant undersize bias), `VARIATION` (sigma times three), `MATERIAL_ISSUE` (15 percent gross deviations with `SURFACE_DAMAGE`), `DOWNTIME` (machine faults, loses one batch slot, restarts).
- The engine reuses domain rules: `evaluate_measurement` decides pass or fail and the defect code, `defect_rate` decides alerts, and `MachineStateTracker` obeys `MACHINE_TRANSITIONS`, so simulated history cannot contain transitions the API would reject.
- Simplifications are explicit: machines run in parallel on a shared clock, every batch takes exactly `minutes_per_batch`, every unit is inspected on every characteristic, one order per `batches_per_order` batches, each machine is dedicated to one product (rotating when there are more products than machines), and consecutive batches share material lots so traceability has something to find.
- Output is plain dataclasses (`SimulationOutput`); `simulation_service.persist` maps them to ORM rows in one transaction and returns counts. The API endpoint is `POST /api/v1/simulation/runs` (role `Engineer`); the seed command runs `database/seeds/demo_scenario.json` through the same path.

## Consequences

Positive:

- Reproducible demonstrations and tests: seed 42 with the demo scenario always produces the same measurements, failures, and alerts.
- The engine is testable in isolation (no database) and fast; persistence is a separate, straightforward mapping.
- Fault signatures are designed to be visible to the investigation rules within a few batches, which makes the end-to-end story demonstrable.
- Domain rules are shared, so there is one definition of pass or fail and of defect rate across the simulator, the API, and the investigation engine.

Negative or accepted costs:

- Realism is limited by design: no queueing between machines, no shift calendars, no partial inspection, no rework. These are documented simplifications, not bugs.
- Row ids and the run tag (`SIMnnnn`, derived from the count of production orders) depend on database state, so persisted identifiers differ between runs even though measurements do not.
- Fault tuning constants (`TOOL_WEAR_RATE`, `CALIBRATION_OFFSET`, `VARIATION_MULTIPLIER`, `MATERIAL_ISSUE_PROBABILITY`) are hard-coded in `faults.py`; changing them changes every scenario.
- Persisting a large run happens within one request; very large parameter values (the schema allows up to 200 batches per machine and 500 units per batch) would make the request slow. Current limits are enforced by `SimulationRequest`.

## Alternatives considered

- Static SQL fixture data. Rejected: a fixed dataset cannot demonstrate different fault scenarios, and generating thousands of consistent inspection rows by hand is error-prone.
- Discrete-event simulation with a real event queue and inter-machine dependencies. Rejected for scope: more realism than the investigation rules can use, at the cost of complexity and harder determinism.
- A simulator that writes directly to the database as it runs. Rejected: it would couple the engine to SQLAlchemy, make unit tests need MySQL, and lose the single-transaction property of persistence.
- Unseeded randomness. Rejected: tests and demonstrations would not be reproducible.
