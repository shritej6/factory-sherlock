# ADR-0004: SQL files as both runtime artefact and documentation source

## Status

Accepted. Recorded 2026-11-03. Implemented in `database/queries/`, `backend/app/repositories/sql_loader.py`, `backend/app/repositories/query_runner.py`.

## Context

The analytical queries are a graded deliverable and also the mechanism behind dashboards, traceability screens, and investigation evidence. If the documented SQL and the executed SQL were different texts (for example documented SQL in a report and ORM expressions or inline strings in Python), reviewers could not be sure that what they read is what runs, and the investigation case board could not show users the real query behind a finding.

## Decision

Keep every non-trivial read query as a standalone `.sql` file under `database/queries/` and execute those files verbatim:

- Nine numbered dashboard and traceability queries (`01_machine_defect_rate_comparison.sql` to `09_daily_production_trend.sql`) and three investigation queries under `database/queries/investigation/`.
- Each file starts with a comment header stating the business question, tables, techniques, parameters, result shape, consumers, and performance notes. `analytics_service.list_query_catalog` exposes these headers to the API (`GET /api/v1/analytics/queries`), which returns `QueryCatalogEntry` objects (`name`, `description`, `sql`, `runnable`, `parameters`) for all twelve files; seven are runnable.
- `sql_loader.py` scans the directory once (cached with `lru_cache`), strips the numeric prefix, and keys subdirectory files with a dotted prefix (`investigation.defect_onset`). `load_sql` returns the raw text; `load_query` wraps it in a SQLAlchemy `text()` clause, declaring expanding bind parameters where a list is passed (`batch_ids`).
- Parameters are always bound (`:window_start`, `:machine_id`, and so on); no query text is built by string formatting. Optional filters use the `(:machine_id IS NULL OR m.id = :machine_id)` pattern inside the SQL.
- `SqlQueryRunner.run` executes a named query and converts `Decimal`, `date`, `datetime`, and `bytes` into JSON-friendly values. Investigation rules receive a `QueryRunner` protocol so they can be tested with a fake.
- Evidence cards persist `query_name`, the full `query_sql` text (header included), and `result_rows` (stored as a JSON object with `columns` and `rows` arrays because MySQL reorders JSON object keys; the API returns a list of row objects in SQL column order), so the investigation screen can show the exact SQL behind every finding.
- The analytics endpoint exposes only the names listed in `analytics_service.DASHBOARD_QUERIES`, with a fixed parameter list per query; forward and backward traces are served by dedicated traceability endpoints.

## Consequences

Positive:

- The SQL a reviewer reads in `database/queries/` is byte-for-byte the SQL the backend executes and the SQL stored on evidence cards.
- Queries can be run and tuned in a MySQL client without touching Python; the comment header doubles as the query's documentation.
- SQL injection is prevented structurally: query text is fixed at load time and only bound parameters vary.
- Adding a query is adding a file; the catalog endpoint picks it up automatically.

Negative or accepted costs:

- Two execution styles coexist (ORM for writes and simple reads, raw SQL for analytics). Developers must know which to use; the module boundary table and this ADR state the rule.
- The loader resolves `database/queries` relative to the backend package (`parents[3]`), so the backend must be run from a checkout that includes the `database/` directory. Packaging the backend alone would break the loader.
- The catalog lists all twelve files, but only seven are runnable through `GET /analytics/queries/{name}`; the others are reached through traceability and investigation endpoints. Clients must not assume every catalog entry is runnable there.
- Result types from MySQL (for example `Decimal` sums of boolean expressions) require the conversion step in `query_runner._jsonable`.

## Alternatives considered

- Inline SQL strings in service modules. Rejected: the documented and executed texts would diverge, and the SQL would be harder to read and review.
- ORM-only queries (SQLAlchemy Core or ORM expressions). Rejected: window functions, LATERAL joins, and ROLLUP are expressible but far less readable than SQL, and the generated SQL could not be shown to users as evidence.
- Database views or stored procedures. Rejected: logic would move into the database where it is harder to version with the code, and evidence cards would show a view name rather than the query.
- A query template engine with string substitution. Rejected: unnecessary given bound parameters and the optional-filter pattern, and it would reopen injection risks.

## Update (2026-11-07)

The decision stands. The counts above are historical: `database/queries/` now holds fourteen files, ten numbered (`01_machine_defect_rate_comparison.sql` to `10_characteristic_control_chart.sql`) and four under `investigation/` (`defect_onset.sql`, `hourly_defect_rates.sql`, `machine_events_before_onset.sql`, `shared_material_lots.sql`). `GET /api/v1/analytics/queries` lists all fourteen; eight are runnable through `GET /analytics/queries/{name}` (`analytics_service.DASHBOARD_QUERIES`, which gained `characteristic_control_chart` with a required `specification_id`), and the other six (the two trace queries and the four investigation queries) run through the traceability and investigation endpoints. Query 10 is the first file whose result the frontend post-processes per row (control limits read from every row), and rule R7 is the first consumer that derives columns in Python (`cusum`, `signal`) from a query result; both keep the executed SQL byte-for-byte identical to the file.
