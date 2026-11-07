# ADR-0002: MySQL 8 as the single system of record

## Status

Accepted. Recorded 2026-11-03. Implemented in `backend/migrations`, `backend/app/models`, `database/`.

## Context

The project is a database systems course deliverable. The schema, constraints, and queries are themselves part of what is being assessed, and the platform's value lies in answering relational questions: which batches consumed a lot, which machine's defect rate rose, which events preceded the rise. The team needed one store that supports foreign keys, CHECK constraints, ENUM columns, window functions, CTEs, LATERAL derived tables, and `GROUP BY ... WITH ROLLUP`, and that runs locally without Docker.

## Decision

Use MySQL 8 (8.4 in `docker-compose.yml`, any 8.x via `scripts/development/local_mysql.sh`) as the only persistent store:

- All operational data (catalog, orders, batches, units, inspections, events, alerts, users) and all investigation output (investigations, evidence cards with their SQL and rows, batch links) live in the same schema of 17 tables.
- Integrity rules that must hold regardless of which code path writes a row are expressed in the database: foreign keys with explicit `ON DELETE` behaviour, `UNIQUE` constraints on natural keys (`code`, `lot_number`, `order_number`, `batch_number`, `serial_number`), CHECK constraints on quantities and on `window_end > window_start`, and ENUM columns for every status.
- Analytical questions are answered by SQL in `database/queries/` executed against the live schema, not by exporting to another engine.
- Evidence rows store query result sets as a `JSON` column because the shape differs per rule.
- The server runs with `utf8mb4`, `utf8mb4_0900_ai_ci`, and strict SQL mode (`STRICT_TRANS_TABLES, NO_ZERO_DATE, NO_ZERO_IN_DATE, ERROR_FOR_DIVISION_BY_ZERO`) in both deployment options.
- The application never connects as root; see ADR-0007.

## Consequences

Positive:

- One transaction boundary per request covers every table, which keeps the multi-table workflows in `production_service.create_batch`, `simulation_service.persist`, and `investigation_service.open_investigation` atomic.
- The database rejects invalid rows even when inserted outside the application (for example by the SQL seed file), which matters when graders or operators run SQL by hand.
- Window functions, CTEs, LATERAL joins, and ROLLUP let the twelve query files express the analytics without application-side aggregation.
- A test database (`<name>_test`) on the same server, selected by `APP_ENV=test`, isolates test data from development data.

Negative or accepted costs:

- MySQL-specific SQL (`LATERAL`, `WITH ROLLUP`, `GROUP_CONCAT`, `DATE_FORMAT`, integer sums of boolean expressions) ties the query files to MySQL. Porting would require rewriting several queries.
- Storing result rows as JSON in `investigation_evidence` duplicates data and means evidence does not update when underlying rows change. This is deliberate: an evidence card is a record of what was observed when the investigation was opened.
- Column type `DateTime` without time zone is used throughout; timestamps are treated as naive local values. The simulation and services use `datetime.now()` consistently, but a future multi-timezone deployment would need a migration.
- `ix_production_units_produced_at` and `ix_inspections_time_result` are chosen by the optimizer only when the requested window is selective; with the whole demo dataset inside the window, EXPLAIN shows a walk from `machines` instead (documented in `docs/database/queries.md`).

## Alternatives considered

- PostgreSQL. Offers equivalent features and stricter typing, but the course and the local tooling targeted MySQL, and MySQL ENUM columns map directly to the application's `StrEnum`s.
- SQLite for development with MySQL in production. Rejected: the query files rely on MySQL-only syntax and the point of the project is to exercise the real engine.
- A separate analytical store or materialised dashboard tables. Rejected: data volumes are small, and keeping analytics as live SQL over the operational schema is what makes the evidence cards reproducible.
- Storing evidence as references to queries only (no stored rows). Rejected: investigations must remain readable after the data changes, and reviewers need to see what the engine saw.

## Update (2026-11-07)

The decision stands. The counts above are historical: the catalogue now holds fourteen query files (ten numbered dashboard and traceability queries, four under `investigation/`), the schema is created by three Alembic revisions (`3a5e982c3679`, `383273c26ef7`, `6c1f0d2a9b47`) and still has 17 tables, and both deployment options now write out the full MySQL 8.4 default `sql_mode`, which adds `ONLY_FULL_GROUP_BY` and `NO_ENGINE_SUBSTITUTION` to the list in the Decision section. Migration `6c1f0d2a9b47` added `ix_inspections_time_id`, `ix_inspections_spec_time`, `ix_production_batches_started_id`, `ix_production_orders_created_id`, and `ix_investigations_created_id` for the paginated list orderings and the control chart window; the EXPLAIN observations are in `docs/database/database-design.md` section 6.
