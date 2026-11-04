# Conversation 2: Simulation engine and the state machine revision

Project area: backend business logic and simulation. Tool: Claude Code. Date: 2026-11-03.
Outcome: substantially revised.

## Sequence

1. Student prompt (paraphrased): build a deterministic simulation engine for three CNC machines with fault injection, without any database code inside the engine.
2. AI proposal: an engine that produces plain dataclasses (orders, batches, units, inspections, events, alerts), seeded from a single random.Random instance, with a MachineStateTracker that reuses the domain transition table.
3. First run: the smoke test raised `InvalidTransitionError: Machine CNC-03 cannot move from WARNING to IDLE`. The generated end-of-run code moved every machine to IDLE, but the transition table (which the AI had also proposed) does not allow WARNING to IDLE.
4. Discussion: two options were considered. Add WARNING to IDLE to the table, or leave a machine with an active fault in WARNING. The second option was chosen because it matches how a real cell would present an unresolved fault and because it makes the dashboard honest.
5. Second revision: the first version rotated products across machines each order, so the demonstration investigation on CNC-03 reported hole position defects on brackets instead of oversize shafts. The engine was changed so each machine is dedicated to one product, and the demo story now matches the project brief.
6. Third revision: the initial tool wear rate (0.015 of tolerance per unit) saturated at a 100 percent failure rate within four batches. It was reduced to 0.008 so the defect rate rises gradually and the onset query has something to detect.

## Verification

- backend/tests/unit/test_simulation_engine.py: same seed gives identical output; different seeds differ; counts follow configuration; tool wear raises failures and leaves the machine in WARNING; downtime skips one batch and walks FAULT, STOPPED, IDLE, RUNNING.
- The persisted demo scenario was inspected in MySQL: CNC-03 ends in WARNING, CNC-01 and CNC-02 in IDLE.

## Student annotation

[Shritej: explain in your own words why the engine returns dataclasses instead of writing rows, and what would break if a second random generator were introduced.]
