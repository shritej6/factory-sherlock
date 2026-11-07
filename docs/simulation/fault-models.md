# Fault models

This document describes each fault kind the virtual factory can inject: the mechanism, the formula applied to measurements, the expected effect on the batch defect rate, the defect types it produces, the machine events and state changes it emits, and how to request it. Constants are defined in `backend/app/simulation/faults.py`; the measurement model is in `backend/app/simulation/measurement.py`; event and state behaviour is in `backend/app/simulation/engine.py`. The overall execution model is in [simulation-design.md](simulation-design.md).

Where this document quotes probabilities, they are computed from the formulas below using the standard normal distribution and are expected values, not results observed from a run. Actual counts for a given seed differ because of random draws.

## Measurement model

For a specification with target `T` and tolerance `tol`, a unit's measured value is:

```
sigma      = (tol / 3) * sigma_multiplier
value      = T + N(0, sigma) + tol * offset_fraction [+ gross term]
measured   = round(value, 3 decimals, ROUND_HALF_UP)
```

The unit passes the characteristic when `abs(measured - T) <= tol` (`domain/quality_rules.py::evaluate_measurement`). With no fault active, `sigma_multiplier = 1`, `offset_fraction = 0`, and the pass limit sits at three standard deviations from the mean, so the natural failure probability per inspection is about 0.27 percent (two-sided tail of the normal distribution beyond three sigma). The module docstring rounds this to "roughly 0.3 percent".

`combined_effect(active, primary_characteristic)` in `faults.py` folds every active fault into one `MeasurementEffect`:

- offsets add (`offset_fraction` is a sum),
- sigma multipliers multiply,
- the gross defect probability is the maximum across active faults.

Faults are per machine. A fault starts at the beginning of the batch whose index equals `start_batch_index` and stays active for the rest of the run; the simulator never clears a fault.

## Failure classification

When a measurement fails, `classify_defect(characteristic, deviation)` chooses the defect type code:

| Characteristic | Positive deviation | Negative deviation |
|----------------|--------------------|--------------------|
| `diameter`, `outer_diameter`, `bore_diameter` | `OVERSIZE_DIAMETER` | `UNDERSIZE_DIAMETER` |
| `hole_position` | `HOLE_POSITION_DEVIATION` | `HOLE_POSITION_DEVIATION` |
| any other (for example `length`, `thickness`) | `DIMENSIONAL_DEVIATION` | `DIMENSIONAL_DEVIATION` |

A failed inspection caused by a gross material deviation additionally carries `SURFACE_DAMAGE`. The simulator only attaches defect codes to inspections whose result is `FAIL`; a passing inspection never has defect links.

## Fault kinds

### TOOL_WEAR

Mechanism: a worn cutting tool removes less material over time, so the dimension it cuts drifts steadily away from target. The model applies a linear mean shift that grows with every unit produced on the machine since the fault started. Only the primary characteristic is affected: the first specification of the product (lowest `product_specifications.id`), because a worn tool changes the dimension it cuts, not every dimension of the part.

Formula (`TOOL_WEAR_RATE = 0.008`):

```
offset_fraction(k) = 0.008 * k        k = units produced since the fault started (0 for the first unit)
value              = T + N(0, tol / 3) + tol * 0.008 * k
```

`ActiveFault.advance()` is called once per unit after all of its inspections, so `k` increases by one per unit regardless of how many specifications the product has.

Expected effect on defect rate: the per-inspection failure probability of the primary characteristic rises slowly at first and then steeply as the mean approaches the tolerance limit. Computed from the formula for `tol / 3` sigma:

| Units since start `k` | Mean offset (fraction of tolerance) | Expected primary failure probability |
|-----------------------|-------------------------------------|--------------------------------------|
| 0 | 0.000 | 0.003 |
| 31 | 0.248 | 0.012 |
| 62 | 0.496 | 0.067 |
| 84 | 0.672 | 0.161 |
| 103 | 0.824 | 0.300 |
| 125 | 1.000 | 0.500 |
| 159 | 1.272 | 0.793 |

For a two-characteristic product with 20 units per batch, the batch defect rate is the mean over 40 inspections, and the secondary characteristic stays at its natural rate. The expected batch defect rate (averaged over the 20 units of each batch, computed from the formula) is approximately 0.003 for the first batch after onset, 0.007, 0.020, 0.048, 0.101, 0.179, 0.273, and 0.361 for the following seven batches. Under this model the simulator's alert threshold of 0.15 is expected to be reached in the sixth batch after onset (units 100 to 119) and the investigation review threshold of 0.10 in the fifth. The exact batch at which a given seed crosses either threshold varies.

Defect types produced: for a diameter characteristic the shift is positive, so failures are `OVERSIZE_DIAMETER`; for `hole_position` they are `HOLE_POSITION_DEVIATION`; for any other characteristic `DIMENSIONAL_DEVIATION`. The engine's event description reads "dimensions drift upward over time".

Events and state changes: at the start of the fault batch, one `machine_events` row with `event_type = TOOL_WEAR`, severity `WARNING`, description "Simulated cutting tool wear: dimensions drift upward over time", and one `STATE_CHANGE` row `RUNNING -> WARNING` with the same description (only if the machine is `RUNNING`). The machine remains `WARNING` at the end of the run. `HIGH_DEFECT_RATE` alerts follow once batches cross `alert_defect_rate`.

Configuration:

```json
{ "machine_code": "CNC-03", "fault": "TOOL_WEAR", "start_batch_index": 4 }
```

### CALIBRATION_DRIFT

Mechanism: a miscalibrated machine or gauge produces a constant bias. The model shifts the mean of every characteristic by a fixed fraction of its tolerance from the first unit of the fault batch onward.

Formula (`CALIBRATION_OFFSET = -0.80`):

```
offset_fraction = -0.80
value           = T + N(0, tol / 3) - 0.80 * tol
```

Expected effect on defect rate: an immediate step change. With the mean 0.8 tolerance below target and sigma of one third of tolerance, the lower limit is 0.6 sigma away, so the expected failure probability per inspection is about 0.274 from the first unit of the fault batch, on every characteristic. The batch defect rate is expected to jump from roughly 0.003 to roughly 0.27 in one batch and stay there, which is above both the alert threshold (0.15) and the investigation review threshold (0.10).

Defect types produced: the shift is negative, so diameters produce `UNDERSIZE_DIAMETER`; `hole_position` produces `HOLE_POSITION_DEVIATION`; other characteristics `DIMENSIONAL_DEVIATION`. The event description reads "constant undersize bias".

Events and state changes: one `CALIBRATION_DRIFT` machine event with severity `WARNING`, description "Simulated calibration error: constant undersize bias", and `RUNNING -> WARNING` if applicable. A `HIGH_DEFECT_RATE` alert is expected on the fault batch itself, and no further alert while the rate stays above threshold.

Configuration:

```json
{ "machine_code": "CNC-01", "fault": "CALIBRATION_DRIFT", "start_batch_index": 3 }
```

### VARIATION

Mechanism: spindle instability, loose fixturing, or similar conditions increase process spread without moving the mean. The model multiplies the standard deviation of every characteristic.

Formula (`VARIATION_MULTIPLIER = 3.0`):

```
sigma_multiplier = 3
value            = T + N(0, tol)
```

Expected effect on defect rate: with sigma equal to the tolerance, the pass limits sit at one sigma, so the expected failure probability per inspection is about 0.317 on every characteristic from the fault batch onward, split roughly evenly between positive and negative deviations. Like calibration drift this is a step change that crosses both thresholds immediately; unlike calibration drift it produces failures in both directions.

Defect types produced: a mix of `OVERSIZE_DIAMETER` and `UNDERSIZE_DIAMETER` on diameter characteristics, `HOLE_POSITION_DEVIATION` or `DIMENSIONAL_DEVIATION` on others.

Events and state changes: the engine has no `VARIATION` value in `MachineEventType`, so the machine event is recorded with `event_type = CALIBRATION_DRIFT`, severity `WARNING`, and the description "Simulated spindle instability: measurement spread increased". The description is the only way to tell the two faults apart in `machine_events`. `RUNNING -> WARNING` as for the other measurement faults.

Configuration:

```json
{ "machine_code": "CNC-02", "fault": "VARIATION", "start_batch_index": 2 }
```

### MATERIAL_ISSUE

Mechanism: a problematic material lot produces intermittent gross defects (inclusions, tearing, scoring) rather than a systematic shift. The model gives each inspection a fixed probability of a large deviation in a random direction, in addition to the normal draw.

Formula (`MATERIAL_ISSUE_PROBABILITY = 0.15`):

```
with probability 0.15:
    direction = +1 or -1 (equal probability)
    value     = T + N(0, tol / 3) + direction * tol * U(1.0, 2.0)
otherwise:
    value     = T + N(0, tol / 3)
```

`U(1.0, 2.0)` is a uniform draw between one and two tolerances, so a gross deviation always lands outside the tolerance band and always fails. The gross-defect check is evaluated per inspection, so two characteristics of the same unit are affected independently.

Expected effect on defect rate: a step change to about 0.152 per inspection (0.15 gross plus the natural rate on the remaining 85 percent), on every characteristic. This sits just above the simulator's alert threshold of 0.15, so with 40 inspections per batch some batches are expected to alert and some are not; it is comfortably above the investigation review threshold of 0.10. The defect pattern is intermittent, which is the signature the investigation engine's shared-lot rule is designed to surface.

Defect types produced: each gross failure carries two codes: the dimensional classification for the direction of the deviation (`OVERSIZE_DIAMETER` or `UNDERSIZE_DIAMETER`, `HOLE_POSITION_DEVIATION`, or `DIMENSIONAL_DEVIATION`) plus `SURFACE_DAMAGE`. The `SURFACE_DAMAGE` code is only ever attached by this fault.

Events and state changes: one `MATERIAL_ISSUE` machine event with severity `WARNING`, description "Simulated material defect: intermittent gross deviations", and `RUNNING -> WARNING`. The fault is attached to a machine, not to a material lot; the lot assignment of the affected batches follows the normal rotation. The simulator does not quarantine any lot.

Configuration:

```json
{ "machine_code": "CNC-01", "fault": "MATERIAL_ISSUE", "start_batch_index": 6 }
```

### DOWNTIME

Mechanism: the machine faults and is restarted; one batch slot is lost. No measurement effect is applied, so quality before and after the downtime is unchanged.

Formula: none. `combined_effect` ignores `DOWNTIME` faults; in fact the engine never appends a `DOWNTIME` fault to the active list.

Expected effect on defect rate: none. The effect is on throughput and on the order: the batch at `start_batch_index` is not produced, the machine's remaining batches shift later by one `minutes_per_batch`, and the production order that owned the lost slot never reaches its planned quantity and stays `IN_PROGRESS`. The dashboard's order completion summary and production performance query show the shortfall.

Defect types produced: none.

Events and state changes, all at the start of the lost batch slot (`clock`) and at `clock + minutes_per_batch`:

1. `machine_events`: `DOWNTIME`, severity `CRITICAL`, description "Simulated unplanned downtime: machine faulted and was restarted", at `clock`.
2. `STATE_CHANGE` `RUNNING -> FAULT` ("Unplanned downtime"), severity `CRITICAL`, at `clock`. If the machine is in `WARNING` from an earlier measurement fault, the transition is `WARNING -> FAULT`.
3. `alerts`: `MACHINE_FAULT`, severity `CRITICAL`, message "<machine> entered FAULT during simulated downtime", at `clock`.
4. `STATE_CHANGE` `FAULT -> STOPPED` ("Fault acknowledged"), `STOPPED -> IDLE` ("Reset after downtime"), `IDLE -> RUNNING` ("Production resumed"), all at `clock + minutes_per_batch`.

Because the machine returns to `RUNNING`, an earlier `WARNING` state is cleared by a later downtime even though the measurement fault remains active; the end-of-run transition then moves the machine to `IDLE`.

Configuration:

```json
{ "machine_code": "CNC-02", "fault": "DOWNTIME", "start_batch_index": 6 }
```

## Combining faults

Several faults may target the same machine at different batch indexes. Their measurement effects combine as described above (offsets add, sigma multipliers multiply, gross probability takes the maximum). Two faults on the same machine with the same `start_batch_index` are not rejected; the engine keeps only the last one listed because it indexes scheduled faults by batch index.

## Requesting faults through the API

`POST /api/v1/simulation/runs` (roles `ENGINEER`, `ADMIN`) accepts a `SimulationRequest` whose `faults` list holds `FaultScenario` objects. `fault` is a string and must be one of `TOOL_WEAR`, `CALIBRATION_DRIFT`, `VARIATION`, `MATERIAL_ISSUE`, `DOWNTIME`; any other value is rejected with HTTP 422 and the message "Unknown fault kind". `machine_code` must match an existing machine, otherwise HTTP 422 with "fault references unknown machine". `start_batch_index` must be zero or greater; an index beyond `batches_per_machine - 1` never fires.

```json
{
  "seed": 42,
  "start_time": "2026-11-02T06:00:00",
  "batches_per_machine": 12,
  "units_per_batch": 20,
  "minutes_per_batch": 30,
  "faults": [
    { "machine_code": "CNC-03", "fault": "TOOL_WEAR", "start_batch_index": 4 },
    { "machine_code": "CNC-02", "fault": "DOWNTIME", "start_batch_index": 6 }
  ]
}
```

This is the body of `database/seeds/demo_scenario.json` (its `description` field is removed by the seed command before validation). `uv run python -m app.seed --demo` runs it against the seeded reference data. The file sets 12 batches of 30 minutes per machine, so the demo covers 06:00 to 12:00 on 2026-11-02, and its description text states one production day (06:00 to 12:00).
