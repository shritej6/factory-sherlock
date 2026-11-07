# Data flow

This document traces five write paths through the backend as sequence diagrams: production batch creation, the CSV inspection import, simulation run persistence, investigation evidence generation, and the overdue order check. Each one is a single database transaction bounded by `get_db_session` in `backend/app/core/database.py`: the session commits when the route handler returns and rolls back when any exception escapes. The overdue check also runs as a command (`app/jobs/check_overdue_orders.py`) that opens and commits its own session. Participants are named after the modules in `backend/app`.

Read paths (lists, traces, dashboard queries) follow the same shape without writes and are not drawn separately. Three of them are worth a sentence because they replaced client-side work: `GET /production-batches?status=` and `GET /investigations?status=` accept a repeatable `status` parameter that the service puts into the `WHERE` clause before `paginate`, so `total` reflects the filter; `GET /production-orders/status-counts` runs one `SELECT status, COUNT(*) ... GROUP BY status` and returns every `OrderStatus` key, zero when absent; and `ProductionBatchRead.order_number` is filled from the `order` relationship, which `list_batches` and `get_batch` load with `selectinload`, so a page of batches costs one extra statement rather than one per row. For the general request pipeline see [component-design.md](component-design.md#request-flow).

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

## Inspection import

Endpoint: `POST /api/v1/inspections/import` (role `Operator`, `multipart/form-data` with one `file` part). Implementation: `inspection_import.import_csv` in `backend/app/services/inspection_import.py`, the parser in `inspection_csv.py`, and `domain.quality_rules.evaluate_measurement` for every row; `BodySizeLimitMiddleware` in `backend/app/api/body_limit.py` guards the request body.

Before the route runs, the body cap answers 413 for a request body over 1 MiB + 64 KiB (file plus multipart framing; 64 KiB on every other route), without reading or spooling the body. The upload is then judged in three passes before anything is written: the parser checks the header and every field and collects row errors; the service resolves serial numbers (upper-cased), characteristics, defect codes, and existing inspections with one query per lookup table and collects more row errors; every row is evaluated in memory with `evaluate_measurement`, the same function the manual `POST /inspections` uses, so pass or fail and the automatic defect code cannot differ between the two entry points. Only when the error list is empty are the rows written, with chunked multi-row `INSERT`s (`BULK_CHUNK_SIZE` 1000) inside a savepoint: `inspections` first, the new ids selected back by (`unit_id`, `specification_id`), then `inspection_defects`. A 5000-row file costs 15 SQL statements including the lookups. A file with any invalid row produces one 422 whose `details.errors` lists every `{row, field, message}`, and no inspection exists afterwards. Limits: 1 MiB, 5000 data rows, 10 defect codes per row.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant R as routes/quality.import_inspections
    participant D as api/deps
    participant I as services/inspection_import
    participant P as services/inspection_csv
    participant Q as domain/quality_rules
    participant S as SQLAlchemy Session
    participant M as MySQL

    C->>R: POST /inspections/import (multipart, file=<csv>)
    Note over C,R: body_limit middleware: 413 when the body is over 1 MiB + 64 KiB
    R->>D: DbSession, Operator
    R->>R: content = file.read(MAX_FILE_BYTES + 1)
    R->>I: import_csv(session, content, content_type, filename)
    I->>I: decode_upload: content type, non-empty, size, utf-8-sig
    alt not a CSV upload, empty, too large, or not UTF-8
        I-->>R: ValidationError 422 (details.errors = [{row: null, field: "file", message}])
    end
    I->>P: parse_csv(text)
    P->>P: header: known, unique, required columns present
    alt header invalid, no data rows, or more than 5000 rows
        P-->>R: ValidationError 422 (file-level or header errors)
    end
    loop each non-blank record
        P->>P: parse serial_number (upper-cased), characteristic, measured_value, inspected_at, defect_type_codes
        P->>P: duplicate (serial, characteristic) within the file?
    end
    P-->>I: (rows, row errors)
    I->>S: _load_lookups: units by serial with product id; all specifications; defect codes; (unit_id, specification_id) pairs already inspected
    S->>M: SELECT production_units JOIN production_batches JOIN production_orders; SELECT product_specifications; SELECT defect_types; SELECT inspections
    loop each parsed row
        I->>I: unit exists? specification for (product, characteristic)? pair not inspected? codes known?
        I->>Q: evaluate_measurement(measured, target, tolerance, characteristic)
        Q-->>I: PASS or FAIL + defect code (no codes allowed on a passing value)
    end
    alt any row error
        I-->>R: ValidationError 422 (details.errors sorted by row, field)
        R-->>D: exception propagates
        D->>M: ROLLBACK
    end
    I->>S: SAVEPOINT (begin_nested)
    I->>S: _bulk_insert(Inspection, rows) in chunks of 1000
    S->>M: INSERT inspections (multi-row)
    I->>S: SELECT unit_id, specification_id, id FROM inspections WHERE unit_id IN (...)
    I->>S: _bulk_insert(InspectionDefect, rows) with mapped inspection_id
    S->>M: INSERT inspection_defects (multi-row)
    alt duplicate key (1062) because another request recorded a pair meanwhile
        S->>M: ROLLBACK TO SAVEPOINT
        I->>S: _existing_pairs(..., locking=True) (SELECT ... FOR UPDATE read)
        I-->>R: ValidationError 422 (row errors "Another import recorded this unit and characteristic first")
    end
    I-->>R: InspectionImportResult (imported, failed_inspections, inspection_ids)
    R-->>D: handler returns
    D->>M: COMMIT
    R-->>C: 201 InspectionImportResult
```

Points worth noting:

- `inspection_csv` never opens a session and never logs, so it is unit tested without MySQL (`tests/unit/test_inspection_csv.py`); the service and route are covered by `tests/api/test_inspection_import.py`, including the rollback of a file with one bad row and the import of `database/seeds/sample_inspection_import.csv` against the demo scenario.
- Row numbers in the errors are 1-based positions below the header, so they match the line numbers a spreadsheet shows minus one; blank lines count.
- Serial numbers are upper-cased before the lookup (stored serials derive from order numbers and machine codes, which are upper case), and characteristics are matched without regard to case against the unit's product; `inspected_at` is optional and defaults to the request time for every row; a `|`-separated defect code list is validated against `defect_types` and rejected on a passing measurement, exactly as for manual entry; `measured_value` must match `[+-]?[0-9]+(\.[0-9]{1,3})?`.
- `_rule_errors` repeats the checks `record_inspection` would raise so that the whole file is reported at once; the `UNIQUE (unit_id, specification_id)` constraint remains the final guard. When it fires during the bulk write (MySQL 1062), `_write_inspections` rolls back to the savepoint, re-reads the pairs with a locking read (a plain read under `REPEATABLE READ` would still show the old snapshot), and reports each conflicting row as a 422 row error with `field: null`; any other integrity error (for example 1452 when a specification was deleted meanwhile) is re-raised for the generic handler in `api/errors.py`.
- Measured on the development database with `scripts/development/benchmark_inspection_import.py` (5000 rows, 250 failing, median of three runs, service call only): one `record_inspection` call per row cost 10507 statements and 1.47 s; the bulk path costs 15 statements and 0.11 s.
- The frontend `ImportInspectionsPanel.tsx` posts the file through `qualityApi.importInspections` (a `FormData` body, so `http.ts` sets no `Content-Type` header), shows the row errors in a table, and refreshes the production query keys on success.

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

Each rule runs one named SQL file through `SqlQueryRunner`, records what it learned on the shared `InvestigationContext`, and returns an `Evidence` card that carries the query name, the full SQL text, and the result rows (for R7 the rows plus two derived columns, `cusum` and `signal`). The service persists the investigation, one `investigation_evidence` row per card (ordered by `sequence`), and one `investigation_batches` junction row per batch that R5 flagged.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant R as routes/investigations.open_investigation
    participant D as api/deps
    participant I as services/investigation_service
    participant K as services/catalog_service
    participant G as investigation/engine.investigate
    participant U as investigation/rules (R1..R7)
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
    G->>U: R7 rule_cusum_onset (machine only, at least 3 hourly rows) -> run("investigation.hourly_defect_rates")
    U->>U: p0 from the first 3 hours; S_t = max(0, S_t-1 + rate - p0 - 0.025); signal at S_t >= 0.10
    U->>U: ctx.cusum_onset_time = first signalling hour
    U-->>G: Evidence R7 (rows + cusum, signal) or None
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
- When `machine_id` is omitted, R1 reports the worst machine in the window, R3, R4, and R7 are skipped, and R5 scans all machines.
- R7 is the only rule whose stored rows differ from the raw query result: `_cusum_rows` adds `cusum` (rounded to four places at every step) and `signal` to each hourly row so a reader can check the statistic by hand. Its narrative compares the signalling hour with the R3 onset, and `build_summary` adds one sentence on whether the two estimates fall in the same hour.
- `product_id` is validated and stored on the investigation but is not passed into `InvestigationContext`; none of the rules filter by product at present.
- Evidence rows store `query_sql` verbatim from the file, including its comment header, which is what the case board shows to users.
- Later status changes (`POST /investigations/{id}/status`) go through `INVESTIGATION_TRANSITIONS`; closing requires a non-empty conclusion and sets `closed_at`.

## Overdue order check

Endpoint: `POST /api/v1/analytics/alerts/checks/overdue-orders` (role `Operator`, no request body). Command: `uv run python -m app.jobs.check_overdue_orders [--as-of ...]` (`make check-overdue`). Implementation: `alert_service.raise_overdue_order_alerts` in `backend/app/services/alert_service.py`.

The check is idempotent per open alert. It selects every order that is not `COMPLETED` or `CANCELLED` and whose `due_date` is before the check date, drops the ones that already have an unacknowledged `ORDER_OVERDUE` alert (found through `alerts.production_order_id`), and adds one alert per remaining order. An order gets a second alert only after the first one has been acknowledged and the order is still open. Severity is `WARNING` for one or two days late and `CRITICAL` from the third day; the alert is stamped with the check date: the server clock for the endpoint, or `--as-of` when the job replays a past check. The orders and their open alerts are read with `SELECT ... FOR UPDATE`, so two checks that overlap run one after the other and the second raises nothing for orders the first already covered.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client or app/jobs/check_overdue_orders
    participant R as routes/analytics.check_overdue_orders
    participant D as api/deps
    participant A as services/alert_service
    participant S as SQLAlchemy Session
    participant M as MySQL

    C->>R: POST /analytics/alerts/checks/overdue-orders (no body)
    R->>D: DbSession, Operator
    R->>A: raise_overdue_order_alerts(session)
    A->>A: moment = _naive(as_of or clock.now()) (as_of is None on this path)
    A->>S: overdue_orders: due_date < moment.date() AND status IN (PLANNED, RELEASED, IN_PROGRESS)
    S->>M: SELECT production_orders ORDER BY due_date, id FOR UPDATE
    A->>S: _orders_with_open_alert: ORDER_OVERDUE, acknowledged_at IS NULL, production_order_id IN (...)
    S->>M: SELECT alerts.production_order_id FOR UPDATE
    loop each overdue order without an open alert
        A->>A: days = days_late(due_date, moment); severity = WARNING if days <= 2 else CRITICAL
        A->>S: add Alert(machine_id, production_order_id, ORDER_OVERDUE, severity, message, created_at = moment)
    end
    A->>S: flush()
    S->>M: INSERT alerts
    A-->>R: OverdueCheckResult (checked, raised, alerts)
    R-->>D: handler returns
    D->>M: COMMIT
    R-->>C: 200 OverdueCheckResponse {checked, raised, alerts[]}
```

Points worth noting:

- `checked` counts the overdue open orders; `raised` counts the new alerts among them, so a second call right after the first returns the same `checked` and `raised: 0`.
- The command path differs in who owns the transaction and in the check date: `check_overdue_orders.run_check` opens `SessionLocal()`, calls the same function with the parsed `--as-of` (or `None`), and commits; `main` logs `{"checked", "raised", "alert_ids"}` as one JSON line and returns 0, or, on any exception, rolls back, logs the traceback under `operation=check_overdue_orders`, and returns 1.
- `due_date` is a `DATE`, so an order due today is on time until midnight; on the command line path, `as_of` with a UTC offset is converted to naive local time and loses its microseconds, matching the `DATETIME` columns.
- Tests: `tests/unit/test_alert_rules.py` (days late, severity, message, open states), `tests/api/test_alert_checks_api.py` (raising, idempotence, re-raising after acknowledgement, the ignored `as_of` body, the real server clock, role guard), `tests/integration/test_alert_order_link.py` (`SET NULL` on order delete, acknowledgement keeps the link, idempotence across sessions, two concurrent checks raise one alert per order, the command's commit and exit codes 0 and 1).

## Seed and reset flows

Not drawn, but related:

- `uv run python -m app.seed [--demo]`: one session; applies `database/seeds/01_reference_data.sql` statement by statement, upserts the four demo users, optionally runs the demo scenario through the simulation path above, then commits once.
- `scripts/development/reset_database.py [--demo]`: reflects and drops every table in the configured database with foreign key checks disabled, then runs `alembic upgrade head` and the seed command as subprocesses.
