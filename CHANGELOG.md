# Changelog

All notable changes to Factory Sherlock are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers will follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once the first release is tagged. No release has been tagged yet, so there is only an Unreleased section.

## [Unreleased]

### Added

- Repository foundation: MIT license, `.editorconfig`, `.gitignore`, `.env.example`, `docker-compose.yml` for an optional MySQL 8.4 service, and `scripts/development/local_mysql.sh` for running MySQL without Docker.
- MySQL schema with 17 tables covering users, products and specifications, machines and machine events, material lots, production orders, batches, and units, inspections and defects, alerts, and investigations with their evidence, created by Alembic revision `3a5e982c3679` (`backend/migrations/versions/20261104_0106_create_manufacturing_schema.py`); revisions `383273c26ef7` (`alerts.production_order_id`) and `6c1f0d2a9b47` (list-ordering indexes) follow it. Every revision has a matching downgrade. A generated DDL snapshot is kept at `database/schema/schema.sql`.
- Database setup script `scripts/setup/init_databases.sh` that creates the application and test databases and a least-privilege application user.
- FastAPI backend under `backend/app` exposing 35 API paths (44 HTTP operations) across auth, catalog, production, quality, traceability, analytics, simulation, investigations, and health, with JWT authentication, role-based authorization, Pydantic validation, and safe error responses carrying request ids. The OpenAPI document is exported to `docs/api/openapi.json`.
- Simulation engine (`backend/app/simulation`) that models machine state, fault injection, and measurement generation to produce production and inspection data.
- Investigation engine (`backend/app/investigation`) with seven rules (R1 to R7): machine defect-rate comparison, dominant defect category, time of deterioration, machine events before onset, batches requiring review, shared material lots, and CUSUM onset detection, producing a summary for each investigation.
- Fourteen documented SQL queries under `database/queries/`: ten numbered reporting, traceability, and control chart queries (eight runnable through `GET /analytics/queries/{name}`) and four investigation queries executed by the engine through bound parameters.
- Seed command `python -m app.seed` that loads reference data from `database/seeds/01_reference_data.sql`, creates the demo accounts, and optionally runs the demo scenario from `database/seeds/demo_scenario.json`; reset script `scripts/development/reset_database.py` that drops all tables and rebuilds from migrations.
- Developer scripts to export the schema (`scripts/development/export_schema.sh`) and the OpenAPI document (`scripts/development/export_openapi.py`).
- Documentation set under `docs/`: architecture, API export, database, simulation, investigation, quality, requirements, development, testing, nine decision records, milestones, media, and AI evidence.
- Governance and CI: five GitHub Actions workflows (Backend CI, Frontend CI, Docs Lint, Compose Smoke, End-to-End); pull request and issue templates; `CONTRIBUTING.md`; `SECURITY.md`; and a root `Makefile` wrapping the development commands.
- Frontend under `frontend/` (React 19, TypeScript, Vite 7, Tailwind 4, TanStack Query, Recharts): login, overview, machines, orders, batches, inspections, traceability, investigations with the show-the-SQL case board, analytics with the SQL explorer, and simulation screens; 118 Vitest tests in 25 files.
- Pagination on the six list endpoints (`production-orders`, `production-batches`, `inspections`, `investigations`, `machines/{id}/events`, `analytics/alerts`): `limit` 1 to 500 (default 50), `offset` at most 1,000,000, response `{items, total, limit, offset}` (`repositories/pagination.py`, `schemas/common.py::Page`); paged tables in the frontend.
- `POST /inspections/import`: CSV upload of at most 1 MiB and 5000 rows, validated row by row with field-level errors, evaluated with the same rule as manual entry, written all or nothing; import panel on the Inspections screen; `database/seeds/sample_inspection_import.csv`; `docs/quality/inspection-import.md`.
- `ORDER_OVERDUE` alerts: `alert_service.raise_overdue_order_alerts` raises one open alert per `PLANNED`, `RELEASED`, or `IN_PROGRESS` order past its due date, through `POST /analytics/alerts/checks/overdue-orders` (Operator), the command `python -m app.jobs.check_overdue_orders`, and `make check-overdue`; migration `383273c26ef7` adds `alerts.production_order_id`; a check button in the overview alerts panel.
- Query 10 `characteristic_control_chart` (X-bar and S by batch with per-subgroup control limits), `GET /specifications`, and the control chart panel on the Analytics screen.
- Rule R7, a one-sided CUSUM over `investigation/hourly_defect_rates.sql`, alongside the LAG-based onset rule R3 (ADR-0009).
- Login throttling in `core/throttle.py`: `LOGIN_MAX_FAILURES` failures per account inside `LOGIN_WINDOW_SECONDS` return 429 with `Retry-After`; the client address counts only for attempts that already failed.
- Request body caps in `api/body_limit.py`: 64 KiB per request, 1 MiB + 64 KiB for the CSV import, answered with 413 `payload_too_large` before authentication.
- Repeatable `status` filter on `GET /production-batches` and `GET /investigations`, `GET /production-orders/status-counts`, and `order_number` on every batch row.
- Migration `6c1f0d2a9b47`: indexes `ix_inspections_time_id`, `ix_inspections_spec_time`, `ix_production_batches_started_id`, `ix_production_orders_created_id`, `ix_investigations_created_id` for the list orderings and the control chart window.
- Playwright end-to-end suite in `frontend/e2e` (9 tests in 5 spec files: login, roles, investigation, traceability, analytics) with `pnpm test:e2e`, run in CI by the End-to-End workflow against a seeded MySQL service; Compose Smoke workflow for the Docker Compose path.
- Benchmarks: `scripts/development/benchmark_simulation.py` (`make benchmark-sim`) and `scripts/development/benchmark_inspection_import.py`.
- Backend tests for every feature above: 481 tests collected (254 unit, 174 API, 53 integration).

### Changed

- List endpoints return the page envelope instead of a bare array; clients must read `items`.
- `POST /analytics/alerts/checks/overdue-orders` takes no request body; the server clock is the check date (`OverdueCheckRequest` removed). The command keeps `--as-of` to replay a past check.
- Query 10 computes `ucl` and `lcl` per row from that row's `sample_count`; the frontend reads the limits from every row and draws them as stepped lines.
- MySQL is started with the full MySQL 8.4 default `sql_mode`, including `ONLY_FULL_GROUP_BY`, by `docker-compose.yml` and `scripts/development/local_mysql.sh`.
- Uvicorn runs with `--no-proxy-headers` in `make backend`, the setup guide, and the Playwright web server so the throttle sees the TCP peer.
- CSV import: `measured_value` must match `[+-]?[0-9]+(\.[0-9]{1,3})?` (so `20.0400` is rejected), serial numbers are matched without regard to case, the reader is strict, and unknown header names are echoed cut to 50 characters.
- Frontend lookups: order counts come from `GET /production-orders/status-counts`, the open investigation count from a filtered `total`, batch status filtering from the server; the batch table reads `order_number` from each row.
- Login page shows the wait from `details.retry_after_seconds` on a 429.

### Fixed

- Login throttle: failures by one user no longer lock other users behind the same address; `ADMIN`, `admin`, and accented spellings share one account bucket; concurrent checks cannot exceed the limit (pending reservation); a missing peer address skips the address dimension.
- Overdue check: concurrent checks serialise on the order rows (`SELECT ... FOR UPDATE`), so at most one open `ORDER_OVERDUE` alert exists per order; the command rolls back, logs the traceback, and exits 1 on any error.
- Catalog writes map only MySQL error 1062 (duplicate key) to 409; other integrity errors reach the generic handlers (`core/mysql_errors.py`).
- Error mapping: MySQL 3819 (CHECK violation) and 1406 (data too long) return 422, connection errors and pool timeouts return 503 "The database is not reachable", other operational errors 503 "The database is unavailable".
- CSV import: malformed CSV structure returns 422 instead of 500; row numbers stay correct when a quoted field spans lines; a unit and characteristic recorded by another import between validation and write returns a 422 row error instead of a 409.
- Frontend: pagination clamps to the last page with rows when the offset passes `total`; mutation errors keep the request id (`ErrorNotice`); the control chart panel reports a failed machine list inline; the overdue check button sends no body.
- Accessibility: the mobile drawer moves focus to its first link and returns it to the Menu button; disclosures and inline row forms return focus to their trigger when they close; the `nav` landmark is labelled "Primary" and the `aside` "Sidebar"; chart titles use the right heading level; row actions carry the batch or alert number in their accessible name; muted text and the request id line meet 4.5:1 contrast in both themes.

### Performance

- Simulation persistence writes units, inspections, defects, and events with chunked multi-row inserts (1000 rows per statement); figures in `docs/simulation/simulation-design.md`.
- CSV import writes with chunked multi-row inserts inside a savepoint: 5000 rows went from 10507 statements and 1.47 s to 15 statements and 0.11 s (`docs/quality/inspection-import.md`).
- List orderings and the control chart window use the indexes from migration `6c1f0d2a9b47`; EXPLAIN results at demo and grown volumes are in `docs/database/database-design.md` section 6.
- Batch lists load the parent order with `selectinload` (constant statement count); the frontend no longer fetches 500-row lookups to count or filter on the client.

### Security

- Login throttling (429 with `Retry-After`), documented in `SECURITY.md` with the proxy header guidance.
- Request body caps (413) before authentication.
- Clients cannot choose the overdue check date; the alert `created_at` is the server clock.
- Paging `offset` bounded at 1,000,000.
- Playwright signs in through `/auth/login` outside the traced browser context so traces never contain the password.

### Documentation

- Architecture, requirements, database, development, testing, quality, and AI evidence documents updated for the features above; `database/schema/schema.sql` and `docs/api/openapi.json` regenerated; ADR-0009 added; diagrams re-rendered where their sources changed.
