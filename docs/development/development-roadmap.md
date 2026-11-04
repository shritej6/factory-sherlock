# Development roadmap

The project brief defines nine phases. This document records the intended scope of each phase and its honest status as of the current repository contents. Status values: Complete (all listed items exist in the repository), In progress (some items exist), Not started.

| Phase | Name | Status |
|-------|------|--------|
| 1 | Repository foundation | Complete with gaps |
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

Present: `LICENSE` (MIT), `.editorconfig`, `.gitignore` (secrets, Python, Node, `.local/`, editors), `.env.example` with every variable documented, `docker-compose.yml`, `scripts/setup/init_databases.sh`, `scripts/development/local_mysql.sh`, `reset_database.py`, `export_schema.sh`, `export_openapi.py`, `backend/pyproject.toml` with `uv.lock`, `frontend/package.json` with `pnpm-lock.yaml`, `backend/README.md`.

Also present: the repository root `README.md` and three GitHub Actions workflows (`backend-ci.yml`, `frontend-ci.yml`, `docs-lint.yml`).

Gaps: `docker-compose.yml` mounts `scripts/setup/init_databases.sh` as `/docker-entrypoint-initdb.d/01_init.sh` and passes `MYSQL_ROOT_ARGS` and `MYSQL_CLIENT_ARGS`, but it has not been executed on this machine because Docker is not installed. The Docker path is therefore unverified; the local MySQL path (`scripts/development/local_mysql.sh`) is the one that has been run. The workflows have not been observed running on GitHub from this checkout.

## Phase 2: Architecture and requirements

Scope: system overview, component design, data flow, repository structure, architecture decision records, database design, simulation and investigation design, functional and non-functional requirements, business rules.

Present: `docs/architecture/system-overview.md`; this documentation set (`docs/simulation/`, `docs/investigation/`, `docs/requirements/`, `docs/testing/`, `docs/development/`, `docs/media/`).

Also present: `docs/architecture/` (system overview, component design, data flow, repository structure), `docs/decisions/` (ADR-0001 to ADR-0008), `docs/database/`, `docs/milestones/`, and `docs/ai_evidence/`.

## Phase 3: Application foundation

Scope: configuration, database engine and session management, structured logging, typed errors and HTTP mapping, password hashing and JWT, role dependencies, health check, ORM models, Alembic migration, seed command.

Present: `backend/app/core/` (clock, config, database, logging, exceptions, security), `backend/app/api/` (deps, errors, router, health, auth), `backend/app/models/` (seven aggregates, enums, timestamp mixin), `backend/migrations/` with one migration creating 17 tables, `backend/app/seed.py` with `database/seeds/01_reference_data.sql`, `database/schema/schema.sql` snapshot, `docs/api/openapi.json`.

Status: complete. Known limits are recorded in `docs/requirements/non-functional-requirements.md` (no request id on successful requests, no rate limiting, no token revocation).

## Phase 4: Manufacturing management

Scope: products and specifications, machines and status changes with events, material lots, defect types, production orders with a state machine, production batches with material consumption and unit generation, batch completion.

Present: `catalog_service.py`, `production_service.py`, routes `catalog.py` and `production.py`, state machines for machines, orders, and batches in `domain/state_machines.py`, schemas in `schemas/catalog.py` and `schemas/production.py`.

Status: complete. Not in scope and not implemented: deleting any entity through the API, pagination of order and batch lists, order overdue alerts (the `ORDER_OVERDUE` alert type exists but is never raised).

## Phase 5: Virtual factory

Scope: deterministic simulation engine, catalog loading, five fault models, measurement generation, machine state tracking, alert generation, persistence in one transaction, API endpoint, demo scenario.

Present: `backend/app/simulation/` (config, faults, measurement, machine_state, events, engine), `simulation_service.py`, route `simulation.py`, `database/seeds/demo_scenario.json`, documentation in `docs/simulation/`.

Status: complete. Known limits (see `docs/simulation/simulation-design.md`): `batches_per_order` and `alert_defect_rate` are not exposed through the API; material lots are not consumed; a VARIATION fault is recorded as a `CALIBRATION_DRIFT` event type; duplicate faults at the same batch index are not rejected.

## Phase 6: Quality and investigation

Scope: inspection recording with server-side evaluation and classification, inspection listing, quality summary, alerts and acknowledgement, investigation engine with rules R1 to R6, evidence cards with SQL and rows, summary builder, investigation lifecycle, SQL query library.

Present: `quality_service.py`, `analytics_service.py`, `investigation_service.py`, `backend/app/investigation/`, routes `quality.py`, `investigations.py`, `analytics.py`, `database/queries/` (nine dashboard queries and three investigation queries), `repositories/sql_loader.py` and `query_runner.py`, documentation in `docs/investigation/investigation-engine.md`.

Status: complete. Planned extensions recorded in the investigation document: per-request thresholds, product-scoped rules, optional narrator.

## Phase 7: Traceability

Scope: batch to lot junction, forward and backward trace queries and endpoints, batch quarantine, lot quarantine with transactional cascade, quarantine blocking lot reuse.

Present: `traceability_service.py`, route `traceability.py`, quarantine endpoint in `production.py`, queries 04 and 05 and `investigation/shared_material_lots.sql`, documentation in `docs/investigation/traceability-design.md`.

Gaps: release from quarantine is not implemented (`QUARANTINED` is terminal for batches; the code comment says re-inspected material is released by creating a new batch); `CONSUMED` lot status is never set; the user who quarantined is not recorded.

## Phase 8: Frontend and analytics

Scope: React, TypeScript, Vite, Tailwind, Recharts single-page application with login, overview dashboard, machines, orders, batches, quality, investigations case board, traceability, simulation, and analytics with a SQL explorer; backend analytics endpoints.

Present (backend): analytics endpoints for the query catalogue (`QueryCatalogEntry`, 12 entries, 7 runnable), parameterised query execution (`QueryResult`), alerts, and acknowledgement (Operator guard). Present (frontend): React 19, TypeScript, Vite 7, Tailwind 4, React Router 7, TanStack Query 5, and Recharts 3 with a screen for each of Login, Overview, Machines, Orders, Batches, Inspections, Traceability, Investigations list, Investigation detail (case board with evidence cards and show-the-SQL), Analytics (charts plus SQL explorer), and Simulation, under `frontend/src/features/*`, with shared UI and chart components, hooks, services, types, and utilities.

Status: complete. `pnpm test` (13 files, 39 tests), `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, and `pnpm build` passed in the last run. Nine screenshots of the running screens were captured on 2026-11-03 (docs/media/screenshots).

## Phase 9: Validation

Scope: automated tests (unit, API, database integration, simulation, business rule, investigation, end-to-end), the twelve required scenarios, test matrix with recorded results, continuous integration, screenshots and demonstration videos, final review of documentation against code.

Present: backend tests under `backend/tests/{unit,api,integration}/` (`uv run pytest`: 100 passed, 95 percent coverage of `app`), frontend tests colocated under `frontend/src` with `frontend/tests/setup.ts` (`pnpm test`: 13 files, 39 tests passed), the CI workflows in `.github/workflows/`, `docs/testing/testing-strategy.md`, `docs/testing/test-matrix.md` (results recorded where an automated test covers the scenario), `docs/media/media-plan.md` (nine screenshots captured; no video yet).

Status: in progress. Next steps in order: execute the Docker path and the GitHub Actions workflows and record the outcome; cover the matrix rows marked as not covered by an automated test; add end-to-end tests under the root `tests/` directory; capture screenshots and videos from the running application.

## Dependencies between remaining work

1. Screenshots and videos (phase 9 media) need the backend and frontend running against the demo data.
2. Confirming the CI workflows requires pushing to a GitHub repository; their MySQL service container matches the local test setup but has not been observed from this machine.
3. Confirming the Docker path requires a machine with Docker installed.
