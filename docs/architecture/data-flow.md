# Data flow

This document traces three representative write paths through the backend as sequence diagrams: production batch creation, simulation run persistence, and investigation evidence generation. Each one is a single database transaction bounded by `get_db_session` in `backend/app/core/database.py`: the session commits when the route handler returns and rolls back when any exception escapes. Participants are named after the modules in `backend/app`.

Read paths (lists, traces, dashboard queries) follow the same shape without writes and are not drawn separately. For the general request pipeline see [component-design.md](component-design.md#request-flow).

## Production batch creation

Endpoint: `POST /api/v1/production-batches` (role `Operator`). Implementation: `production_service.create_batch` in `backend/app/services/production_service.py`.

A batch is the unit of traceability, so starting one writes four kinds of row at once: the order status may move from `RELEASED` to `IN_PROGRESS`, the `production_batches` row is inserted, one `batch_materials` junction row per consumed material lot, and one `production_units` row per unit with a generated serial number. Any validation failure before the flush leaves nothing in the database; any constraint failure during the flush rolls the whole request back.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant R as routes/production.create_batch
    participant D as api/deps
    participant P as services/production_service
    participant K as services/catalog_service
    participant S as SQLAlchemy Session
    participant M as MySQL

    C->>R: POST /production-batches {production_order_id, quantity, materials[]}
    R->>D: DbSession (get_db_session opens Session)
    R->>D: Operator (decode JWT, load User, check role)
    D->>M: SELECT users WHERE id = sub
    D-->>R: User
    R->>P: create_batch(session, ProductionBatchCreate)
    P->>S: session.get(ProductionOrder, id)
    S->>M: SELECT production_orders
    alt order missing
        P-->>R: NotFoundError (404)
    end
    P->>P: status in {RELEASED, IN_PROGRESS}? machine assigned?
    P->>S: SUM(quantity) of IN_PROGRESS batches for the order
    S->>M: SELECT COALESCE(SUM(quantity),0) FROM production_batches
    P->>P: quantity <= remaining - in_progress?
    P->>P: material lot ids unique?
    loop each material
        P->>K: get_material_lot(session, lot_id)
        K->>M: SELECT material_lots
        P->>P: lot.status is AVAILABLE?
    end
    alt any rule fails
        P-->>R: ValidationError (422)
        R-->>D: exception propagates
        D->>M: ROLLBACK
    end
    P->>P: order.status = IN_PROGRESS (if RELEASED)
    P->>P: next_batch_number -> "<order>-Bnn"
    P->>S: add(ProductionBatch + BatchMaterial[] + ProductionUnit[1..quantity])
    P->>S: flush() via _flush_or_conflict
    S->>M: UPDATE production_orders; INSERT production_batches; INSERT batch_materials; INSERT production_units
    alt duplicate batch_number
        M-->>S: IntegrityError
        P-->>R: ConflictError (409)
    end
    P-->>R: ProductionBatch
    R->>R: ProductionBatchRead.model_validate(batch)
    R-->>D: handler returns
    D->>M: COMMIT
    R-->>C: 201 ProductionBatchRead
```

Points worth noting:

- The serial number format is `<batch_number>-Unnnn` and `produced_at` is set to the batch start time for every unit; units are created up front so inspections can reference them.
- The batch number is derived from a count of existing batches for the order; the `UNIQUE` constraint on `batch_number` is the real guard against concurrent duplicates and is surfaced as 409.
- Completing a batch later (`POST /production-batches/{id}/complete`) is a separate transaction that moves the batch to `COMPLETED`, adds its quantity to `order.quantity_completed`, and marks the order `COMPLETED` when the planned quantity is reached.

## Simulation run persistence

Endpoint: `POST /api/v1/simulation/runs` (role `Engineer`). Implementation: `simulation_service.run_simulation` in `backend/app/services/simulation_service.py`. The same function is called by `app/seed.py --demo` with `database/seeds/demo_scenario.json`.

The engine is pure: it receives reference rows already loaded from MySQL and returns dataclasses. The service then writes those dataclasses in one transaction: orders, batches, batch materials, and alerts as ORM objects (there are few of them), and units, inspections, inspection defects, and machine events as chunked multi-row `INSERT` statements of at most 1000 rows (`simulation_service.BULK_CHUNK_SIZE`). Because MySQL returns no generated ids for a multi-row insert, the service selects `serial_number, id` back after the unit insert and `unit_id, specification_id, id` after the inspection insert, and uses those natural keys to build the dependent rows. A run of 3 machines, 12 batches each, 20 units per batch, and 2 specifications per product writes 9 orders, about 36 batches, about 720 units, about 1,440 inspections, plus events and alerts, or nothing at all.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client or app/seed.py
    participant R as routes/simulation.run_simulation
    participant D as api/deps
    participant V as services/simulation_service
    participant E as simulation/engine.SimulationEngine
    participant Q as domain/quality_rules + state_machines
    participant S as SQLAlchemy Session
    participant M as MySQL

    C->>R: POST /simulation/runs {seed, start_time, batches_per_machine, units_per_batch, minutes_per_batch, faults[]}
    R->>D: DbSession, Engineer
    R->>V: run_simulation(session, SimulationRequest)
    V->>S: load_catalog: products + specifications, machines, AVAILABLE material lots, defect types
    S->>M: SELECT products, product_specifications, machines, material_lots, defect_types
    alt a product has no available lot
        V-->>R: ValidationError (422)
    end
    V->>V: to_config -> SimulationConfig (ValidationError on unknown fault kind)
    V->>E: SimulationEngine(config, catalog).run()
    loop each machine, each batch index
        E->>E: open SimulatedOrder every batches_per_order batches
        E->>E: inject fault if scheduled (events, WARNING or FAULT state, alerts)
        loop each unit, each specification
            E->>Q: evaluate_measurement(measured, target, tolerance, characteristic)
            Q-->>E: PASS or FAIL + defect code
        end
        E->>Q: defect_rate(failed, inspected) -> HIGH_DEFECT_RATE alert if >= 0.15
    end
    E-->>V: SimulationOutput (orders, batches, state_changes, fault_events, alerts, final_states)
    V->>S: _next_run_tag: COUNT(production_orders) -> "SIMnnnn"
    V->>S: _persist_orders: add ProductionOrder per SimulatedOrder; flush()
    S->>M: INSERT production_orders
    V->>S: _persist_batches: add ProductionBatch (COMPLETED) + BatchMaterial[] per SimulatedBatch; flush()
    S->>M: INSERT production_batches, batch_materials
    V->>V: _complete_orders: quantity_completed per order; COMPLETED when planned reached
    V->>S: _bulk_insert(ProductionUnit, rows) in chunks of 1000
    S->>M: INSERT production_units (multi-row)
    V->>S: _unit_ids_by_serial: SELECT serial_number, id WHERE batch_id IN (run batches)
    V->>S: _bulk_insert(Inspection, rows) with mapped unit_id
    S->>M: INSERT inspections (multi-row)
    V->>S: _inspection_ids_by_unit_and_spec: SELECT unit_id, specification_id, id for the run batches
    V->>S: _bulk_insert(InspectionDefect, rows) with mapped inspection_id
    S->>M: INSERT inspection_defects (multi-row)
    V->>S: _bulk_insert(MachineEvent, rows) for state changes and fault events
    S->>M: INSERT machine_events (multi-row)
    V->>S: add Alert per SimulatedAlert
    V->>S: set Machine.status from final_states
    V->>S: flush()
    S->>M: INSERT alerts; UPDATE production_orders, machines
    V-->>R: SimulationResult (counts)
    R-->>D: handler returns
    D->>M: COMMIT
    R-->>C: 201 SimulationResult
```

Points worth noting:

- Determinism: all randomness comes from `random.Random(config.seed)`; the same request against the same catalog produces the same measurements. Row ids and the `SIMnnnn` run tag depend on database state, so repeated runs produce distinct order numbers but identical measurement sequences.
- Material lots are not marked `CONSUMED` by the simulation; `quantity_used` is recorded per batch in `batch_materials` and lot status remains `AVAILABLE` unless a lot is quarantined.
- Order numbers are `SIMnnnn-<machine code>-nn`, batch numbers append `-Bnn`, serial numbers append `-Unnnn`, matching the manual path's format.
- The bulk statements run on the same session and therefore inside the same transaction as the ORM writes; `tests/integration/test_transactions.py` fails the `machine_events` insert, the last bulk step, and asserts that no orders, batches, units, or inspections remain. Timings before and after the switch to bulk inserts are in `docs/simulation/simulation-design.md` under "Persistence path".

## Investigation evidence generation

Endpoint: `POST /api/v1/investigations` (role `Engineer`). Implementation: `investigation_service.open_investigation` in `backend/app/services/investigation_service.py`, `investigation/engine.investigate`, and the rules in `investigation/rules.py`.

Each rule runs one named SQL file through `SqlQueryRunner`, records what it learned on the shared `InvestigationContext`, and returns an `Evidence` card that carries the query name, the full SQL text, and the result rows. The service persists the investigation, one `investigation_evidence` row per card (ordered by `sequence`), and one `investigation_batches` junction row per batch that R5 flagged.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant R as routes/investigations.open_investigation
    participant D as api/deps
    participant I as services/investigation_service
    participant K as services/catalog_service
    participant G as investigation/engine.investigate
    participant U as investigation/rules (R1..R6)
    participant Y as investigation/summary
    participant Q as repositories/SqlQueryRunner
    participant L as repositories/sql_loader
    participant S as SQLAlchemy Session
    participant M as MySQL

    C->>R: POST /investigations {title, machine_id?, product_id?, window_start, window_end}
    R->>D: DbSession, Engineer
    R->>I: open_investigation(session, InvestigationCreate, user_id)
    I->>I: window_end > window_start? else ValidationError
    opt machine_id given
        I->>K: get_machine -> machine_code (NotFoundError if absent)
    end
    opt product_id given
        I->>K: get_product (existence only)
    end
    I->>G: investigate(InvestigationContext, SqlQueryRunner(session))
    G->>U: R1 rule_defect_rate_elevation
    U->>Q: run("machine_defect_rate_comparison", window)
    Q->>L: load_query(name)
    L-->>Q: TextClause from database/queries/01_*.sql
    Q->>M: execute with bound params
    M-->>Q: rows
    Q-->>U: JSON-friendly rows
    U->>U: ctx.machine_rate, fleet_rate, elevated
    U-->>G: Evidence R1 (narrative, query_name, query_sql, rows)
    G->>U: R2 rule_dominant_defect -> run("recurring_defects")
    U-->>G: Evidence R2 or None
    G->>U: R3 rule_defect_onset (machine only) -> run("investigation.defect_onset")
    U->>U: ctx.onset_time = first hour >= batch_review_rate
    U-->>G: Evidence R3 or None
    G->>U: R4 rule_related_machine_events (needs onset) -> run("investigation.machine_events_before_onset")
    U-->>G: Evidence R4 or None
    G->>U: R5 rule_affected_batches -> run("batches_requiring_review", threshold 0.10)
    U->>U: ctx.affected_batch_ids
    U-->>G: Evidence R5
    G->>U: R6 rule_shared_material_lots (needs batches) -> run("investigation.shared_material_lots", batch_ids expanding)
    U-->>G: Evidence R6 or None
    G->>Y: build_summary(ctx)
    Y-->>G: summary text
    G-->>I: InvestigationReport (evidence[], summary, affected_batch_ids, elevated)
    I->>S: add Investigation + InvestigationEvidence[seq 1..n] + InvestigationBatch[] ; flush()
    S->>M: INSERT investigations, investigation_evidence (result_rows as JSON: a `columns` list plus `rows` value arrays), investigation_batches
    I->>S: get_investigation (selectinload evidence, batch_links)
    I-->>R: Investigation
    R->>R: InvestigationRead.model_validate
    R-->>D: handler returns
    D->>M: COMMIT
    R-->>C: 201 InvestigationRead with evidence cards
```

Points worth noting:

- The rules execute inside the same transaction as the insert, so evidence reflects a consistent snapshot at `REPEATABLE READ` (MySQL InnoDB default).
- When `machine_id` is omitted, R1 reports the worst machine in the window, R3 and R4 are skipped, and R5 scans all machines.
- `product_id` is validated and stored on the investigation but is not passed into `InvestigationContext`; none of the rules filter by product at present.
- Evidence rows store `query_sql` verbatim from the file, including its comment header, which is what the case board shows to users.
- Later status changes (`POST /investigations/{id}/status`) go through `INVESTIGATION_TRANSITIONS`; closing requires a non-empty conclusion and sets `closed_at`.

## Seed and reset flows

Not drawn, but related:

- `uv run python -m app.seed [--demo]`: one session; applies `database/seeds/01_reference_data.sql` statement by statement, upserts the four demo users, optionally runs the demo scenario through the simulation path above, then commits once.
- `scripts/development/reset_database.py [--demo]`: reflects and drops every table in the configured database with foreign key checks disabled, then runs `alembic upgrade head` and the seed command as subprocesses.
