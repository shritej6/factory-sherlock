# Development roadmap

The project brief defines nine phases. This document records the intended scope of each phase and its status as of 2026-11-07, read from the repository contents. Status values: Complete (all listed items exist in the repository), Complete with gaps (the phase is usable but a listed limit remains), In progress (some items exist), Not started.

| Phase | Name | Status |
|-------|------|--------|
| 1 | Repository foundation | Complete |
| 2 | Architecture and requirements | Complete |
| 3 | Application foundation | Complete |
| 4 | Manufacturing management | Complete |
| 5 | Virtual factory | Complete |
| 6 | Quality and investigation | Complete |
| 7 | Traceability | Complete with gaps |
| 8 | Frontend and analytics | Complete |
| 9 | Validation | In progress |

## Phase 1: Repository foundation

Scope: repository layout, licensing, editor and ignore configuration, environment template, database bootstrap scripts, dependency locking.

Present: `LICENSE` (MIT), `.editorconfig`, `.gitignore` (secrets, Python, Node, `.local/`, editors), `.env.example` with every variable documented, `docker-compose.yml`, `scripts/setup/init_databases.sh`, `scripts/development/local_mysql.sh`, `reset_database.py`, `export_schema.sh`, `export_openapi.py`, `benchmark_simulation.py`, `backend/pyproject.toml` with `uv.lock`, `frontend/package.json` with `pnpm-lock.yaml`, `backend/README.md`.

Also present: the repository root `README.md` and five GitHub Actions workflows: `backend-ci.yml` (Backend CI), `frontend-ci.yml` (Frontend CI), `docs-lint.yml` (Docs Lint), `compose-smoke.yml` (Compose Smoke), and `e2e.yml` (End-to-End).

Docker path: `docker-compose.yml` mounts `scripts/setup/init_databases.sh` as `/docker-entrypoint-initdb.d/01_init.sh` and passes `MYSQL_ROOT_ARGS` and `MYSQL_CLIENT_ARGS`. Docker is not installed on the development machine, so the local MySQL path (`scripts/development/local_mysql.sh`) is the one run by hand and the Docker path is verified by the Compose Smoke workflow, which starts the `mysql` service from a `.env` built out of `.env.example`, checks the schemas, their collation, and the application user's grants as root inside the container, and connects as the application user from the runner. It runs on every push and pull request that changes `docker-compose.yml`, `scripts/setup/`, `.env.example`, or the workflow itself.

## Phase 2: Architecture and requirements

Scope: system overview, component design, data flow, repository structure, architecture decision records, database design, simulation and investigation design, functional and non-functional requirements, business rules.

Present: `docs/architecture/system-overview.md`; this documentation set (`docs/simulation/`, `docs/investigation/`, `docs/requirements/`, `docs/testing/`, `docs/development/`, `docs/media/`, `docs/quality/`).

Also present: `docs/architecture/` (system overview, component design, data flow, repository structure), `docs/decisions/` (ADR-0001 to ADR-0011), `docs/database/`, `docs/milestones/`, and `docs/ai_evidence/`.

## Phase 3: Application foundation

Scope: configuration, database engine and session management, structured logging, typed errors and HTTP mapping, password hashing and JWT, role dependencies, health check, ORM models, Alembic migration, seed command.

Present: `backend/app/core/` (clock, config, database, logging, exceptions, security, throttle), `backend/app/api/` (deps with the `Paging` dependency, errors, router, health, auth), `backend/app/models/` (seven aggregates, enums, timestamp mixin), `backend/migrations/` with three migrations (`3a5e982c3679` creates the 17 tables; `383273c26ef7` adds `alerts.production_order_id`; `6c1f0d2a9b47` adds the list-ordering indexes), `backend/app/seed.py` with `database/seeds/01_reference_data.sql`, `database/schema/schema.sql` snapshot, `docs/api/openapi.json`.

Status: complete. Login is throttled per account before the password is verified, and per client address only for attempts that already failed (`core/throttle.py`, NFR-1.11); request bodies are capped before authentication (`api/body_limit.py`, 64 KiB, 1 MiB + 64 KiB for the CSV import). Known limits are recorded in `docs/requirements/non-functional-requirements.md` (no request id on successful requests, no rate limit on authenticated endpoints, no token revocation).

## Phase 4: Manufacturing management

Scope: products and specifications, machines and status changes with events, material lots, defect types, production orders with a state machine, production batches with material consumption and unit generation, batch completion.

Present: `catalog_service.py`, `production_service.py`, routes `catalog.py` and `production.py`, state machines for machines, orders, and batches in `domain/state_machines.py`, schemas in `schemas/catalog.py` and `schemas/production.py`.

Status: complete. Order and batch lists are paginated (`GET /production-orders`, `GET /production-batches`: `limit` 1 to 500, default 50, `offset`, response `{items, total, limit, offset}`; `repositories/pagination.py`). `GET /production-batches` takes a repeatable `status` filter applied before pagination and returns `order_number` on every row; `GET /production-orders/status-counts` returns one count per order status from a single `GROUP BY`. `ORDER_OVERDUE` alerts are raised by the on-demand check in `services/alert_service.py` (`POST /analytics/alerts/checks/overdue-orders`, `make check-overdue`; BR-100 to BR-104). Not in scope and not implemented: deleting any entity through the API.

## Phase 5: Virtual factory

Scope: deterministic simulation engine, catalog loading, five fault models, measurement generation, machine state tracking, alert generation, persistence in one transaction, API endpoint, demo scenario.

Present: `backend/app/simulation/` (config, faults, measurement, machine_state, events, engine), `simulation_service.py` (orders, batches, and alerts through the ORM; units, inspections, defects, and events as chunked multi-row inserts), route `simulation.py`, `database/seeds/demo_scenario.json`, `scripts/development/benchmark_simulation.py`, documentation in `docs/simulation/`.

Status: complete. Known limits (see `docs/simulation/simulation-design.md`): `batches_per_order` and `alert_defect_rate` are not exposed through the API; material lots are not consumed; a VARIATION fault is recorded as a `CALIBRATION_DRIFT` event type; duplicate faults at the same batch index are not rejected.

## Phase 6: Quality and investigation

Scope: inspection recording with server-side evaluation and classification, inspection import from CSV, inspection listing, quality summary, alerts and acknowledgement, investigation engine with rules R1 to R7, evidence cards with SQL and rows, summary builder, investigation lifecycle, SQL query library.

Present: `quality_service.py`, `inspection_csv.py` and `inspection_import.py` (`POST /inspections/import`, `docs/quality/inspection-import.md`), `analytics_service.py`, `alert_service.py`, `investigation_service.py`, `backend/app/investigation/`, routes `quality.py`, `investigations.py`, `analytics.py`, `database/queries/` (ten dashboard and traceability queries and four investigation queries), `repositories/sql_loader.py` and `query_runner.py`, documentation in `docs/investigation/investigation-engine.md`.

Status: complete. R7 (CUSUM onset detection over `investigation/hourly_defect_rates.sql`) was added on 2026-11-07. Planned extensions recorded in the investigation document: per-request thresholds, product-scoped rules, optional narrator.

## Phase 7: Traceability

Scope: batch to lot junction, forward and backward trace queries and endpoints, batch quarantine, lot quarantine with transactional cascade, quarantine blocking lot reuse.

Present: `traceability_service.py`, route `traceability.py`, quarantine endpoint in `production.py`, queries 04 and 05 and `investigation/shared_material_lots.sql`, documentation in `docs/investigation/traceability-design.md`.

Gaps: release from quarantine is not implemented (`QUARANTINED` is terminal for batches; the code comment says re-inspected material is released by creating a new batch); the `CONSUMED` lot status exists in `models/enums.py` but no service sets it; the user who quarantined is not recorded. None of these changed on 2026-11-07.

## Phase 8: Frontend and analytics

Scope: React, TypeScript, Vite, Tailwind, Recharts single-page application with login, overview dashboard, machines, orders, batches, quality, investigations case board, traceability, simulation, and analytics with a SQL explorer; backend analytics endpoints.

Layout since 2026-11-08: the shell is `StatusBand.tsx` above the page and `SoftKeyBar.tsx` below it, in one black theme (ADR-0011). The sidebar and the mobile drawer named in earlier entries below no longer exist.

Present (backend): analytics endpoints for the query catalogue (`QueryCatalogEntry`, 14 entries, 8 runnable), parameterised query execution (`QueryResult`, including query 10 `characteristic_control_chart` with `specification_id`), `GET /specifications` for the control chart picker, paginated alerts, acknowledgement (Operator guard), and the overdue order check. Present (frontend): React 19, TypeScript, Vite 7, Tailwind 4, React Router 7, TanStack Query 5, and Recharts 3 with a screen for each of Login, Overview, Machines, Orders, Batches, Inspections (with the CSV import panel), Traceability, Investigations list, Investigation detail (case board with evidence cards and show-the-SQL), Analytics (charts, the per-characteristic control chart, and the SQL explorer), and Simulation, under `frontend/src/features/*`, with shared UI and chart components, hooks, services, types, and utilities; the list screens read the page envelope of the paginated endpoints.

Status: complete. `pnpm test` ran 25 files and 118 tests, all passing, on 2026-11-07 in this checkout; `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, and `pnpm build` passed in the last recorded run (commit 897fb3e, 2026-11-07). An accessibility pass on 2026-11-07 (commit f62170c) covered focus management, landmark and heading structure, accessible names for repeated row actions, and contrast. Fourteen screenshots of the running screens were captured on 2026-11-07 (docs/media/screenshots).

## Phase 9: Validation

Scope: automated tests (unit, API, database integration, simulation, business rule, investigation, end-to-end), the twelve required scenarios, test matrix with recorded results, continuous integration, screenshots and demonstration videos, final review of documentation against code.

Present: backend tests under `backend/tests/{unit,api,integration}/` (481 tests collected on 2026-11-07 in 13 unit, 16 API, and 6 integration files, including `test_pagination_api.py`, `test_inspection_csv.py`, `test_inspection_import.py`, `test_body_limit.py`, `test_body_limit_api.py`, `test_alert_rules.py`, `test_alert_checks_api.py`, `test_alert_order_link.py`, `test_login_throttle.py`, `test_login_throttle_api.py`, `test_error_mapping.py`, `test_status_filters_api.py`, and `test_list_ordering_indexes.py`; the suite was not run against MySQL from this checkout, and the last recorded run with results is in `docs/testing/test-matrix.md`), frontend tests colocated under `frontend/src` with `frontend/tests/setup.ts` (`pnpm test`: 25 files, 118 tests passed on 2026-11-07), end-to-end browser tests under `frontend/e2e` (Playwright Test, five spec files and nine tests: login, roles, investigation, traceability, analytics; `pnpm test:e2e` starts the backend on port 8013 and Vite on port 5183), the five CI workflows in `.github/workflows/`, `docs/testing/testing-strategy.md`, `docs/testing/test-matrix.md` (results recorded where an automated test covers the scenario), `docs/media/media-plan.md` (fourteen screenshots captured; silent clips for videos 2 to 6 committed under ADR-0010, narration pending).

Gaps: the matrix rows marked as not covered by an automated test remain; the walkthrough video is being produced.

Status: in progress. All five workflows passed on the first push of the integration branch on 2026-11-08 (run ids in `docs/testing/test-matrix.md`). Next steps in order: cover the matrix rows not yet covered by an automated test; finish the walkthrough video; final review of documentation against code.

## Roadmap items added after the Week 10 report

| Item | Status on 2026-11-07 | Where |
|------|----------------------|-------|
| Pagination of list endpoints | Implemented | `repositories/pagination.py`, `schemas/common.py::Page`, six routes; `tests/api/test_pagination_api.py` |
| CSV inspection import | Implemented | `POST /inspections/import`, `services/inspection_csv.py`, `services/inspection_import.py`, `frontend/src/features/quality/ImportInspectionsPanel.tsx`; `docs/quality/inspection-import.md` |
| ORDER_OVERDUE alerts | Implemented | `services/alert_service.py`, `jobs/check_overdue_orders.py`, migration `383273c26ef7`; BR-100 to BR-104 |
| Per-characteristic control chart | Implemented | `database/queries/10_characteristic_control_chart.sql`, `GET /specifications`, `frontend/src/features/analytics/ControlChartPanel.tsx` |
| CUSUM onset rule (R7) | Implemented | `investigation/rules.py::rule_cusum_onset`, `database/queries/investigation/hourly_defect_rates.sql` |
| Login throttle | Implemented | `core/throttle.py`; NFR-1.11, `SECURITY.md` |
| Bulk-insert simulation persistence | Implemented | `simulation_service._bulk_insert`; figures in `docs/simulation/simulation-design.md` |
| End-to-end tests and Compose Smoke in CI | Implemented | `frontend/e2e`, `.github/workflows/e2e.yml`, `.github/workflows/compose-smoke.yml` |
| Login throttle redesign (account lockout before verification, address rule only after a failure, username normalisation, pending reservation) | Implemented | `core/throttle.py`; `tests/unit/test_login_throttle.py` (16 tests), `tests/api/test_login_throttle_api.py` (10 tests) |
| Bulk CSV import write path | Implemented | `services/inspection_import.py::_write_inspections`; `scripts/development/benchmark_inspection_import.py`; figures in `docs/quality/inspection-import.md` |
| Request body caps (413 before authentication) | Implemented | `api/body_limit.py`; `tests/unit/test_body_limit.py`, `tests/api/test_body_limit_api.py` |
| Per-subgroup control limits | Implemented | `database/queries/10_characteristic_control_chart.sql`; `frontend/src/utils/chartTransforms.ts` reads `ucl` and `lcl` per row |
| List-ordering indexes | Implemented | migration `6c1f0d2a9b47`; `tests/integration/test_list_ordering_indexes.py`; EXPLAIN notes in `docs/database/database-design.md` section 6 |
| Status filters and order status counts | Implemented | `GET /production-batches?status=`, `GET /investigations?status=`, `GET /production-orders/status-counts`, `order_number` on batch rows; `tests/api/test_status_filters_api.py` |
| Overdue check without a client-supplied date | Implemented | `routes/analytics.py::check_overdue_orders` (no body), locking reads in `alert_service.py`, exit 1 on error in `jobs/check_overdue_orders.py`; `tests/api/test_alert_checks_api.py` |
| Frontend accessibility pass | Implemented | commit f62170c: `components/ui/States.tsx` (`ErrorNotice`), `Disclosure.tsx`, `app/Sidebar.tsx`, `charts/ChartFrame.tsx`, `features/batches/BatchActions.tsx` |
| Industrial control panel interface | Implemented | commit 3a6ccad, ADR-0011: `app/StatusBand.tsx`, `app/SoftKeyBar.tsx`, `styles/index.css`, `utils/chartTheme.ts`; `Sidebar.tsx` and `hooks/useMediaQuery.ts` removed |
| Walkthrough video | In progress | `docs/media/media-plan.md`; `docs/media/videos/` holds no video file |

## Dependencies between remaining work

1. The walkthrough video (phase 9 media) needs the backend and frontend running against the demo data.
2. The three original CI workflows ran green on the first push to GitHub on 2026-11-04 (Backend CI run 41779775539, Frontend CI run 41779775057, Docs Lint run 41779775596; see https://github.com/shritej6/factory-sherlock/actions). The backend job created the databases with the setup script, applied the migration, and ran the full suite against the MySQL 8.4 service container. Compose Smoke and End-to-End were added on 2026-11-07. On the first push of `feature/completion-integration` (commit 0de489b, 2026-11-08) all five passed: Backend CI run 42568859627, Frontend CI run 42568859552, Docs Lint run 42568859579, Compose Smoke run 42568859629, End-to-End run 42568859641.
3. The Docker path is verified by the Compose Smoke workflow, so no local Docker installation is needed to confirm it.
