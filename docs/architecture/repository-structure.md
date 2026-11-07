# Repository structure

This document is the file-level map of the Factory Sherlock repository. The directory tree was generated from the filesystem on 2026-11-07. It leaves out files that `.gitignore` excludes (`.env`, `.coverage`, `*.tsbuildinfo`) and the directories `node_modules`, `.venv`, `.local`, `__pycache__`, `dist`, `.git`, and the Playwright output directories `test-results` and `playwright-report`. The backend is described file by file; `database/` and `scripts/` are described per file; the frontend and the documentation tree are described at directory level.

Status values: Implemented (code exists and matches the description), In progress (partially present or actively changing), Planned (directory or hook exists, content does not).

Regenerate the tree with:

```bash
python3 -c "
from pathlib import Path
EX={'node_modules','.venv','.local','__pycache__','dist','.git','.pytest_cache','.ruff_cache','.mypy_cache','.DS_Store','.env','.coverage','test-results','playwright-report'}
def walk(d,p,o):
    es=sorted([x for x in d.iterdir() if x.name not in EX and x.suffix!='.tsbuildinfo'],key=lambda x:(not x.is_dir(),x.name.lower()))
    for i,x in enumerate(es):
        last=i==len(es)-1; o.append(f\"{p}{'\`-- ' if last else '|-- '}{x.name}{'/' if x.is_dir() else ''}\")
        if x.is_dir(): walk(x,p+('    ' if last else '|   '),o)
o=['factory-sherlock/']; walk(Path('.'),'',o); print('\n'.join(o))"
```

## Directory tree

```text
factory-sherlock/
|-- .github/
|   |-- ISSUE_TEMPLATE/
|   |   |-- bug_report.md
|   |   |-- config.yml
|   |   |-- database_change.md
|   |   `-- feature_request.md
|   |-- workflows/
|   |   |-- backend-ci.yml
|   |   |-- compose-smoke.yml
|   |   |-- docs-lint.yml
|   |   |-- e2e.yml
|   |   `-- frontend-ci.yml
|   `-- pull_request_template.md
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- routes/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- analytics.py
|   |   |   |   |-- auth.py
|   |   |   |   |-- catalog.py
|   |   |   |   |-- health.py
|   |   |   |   |-- investigations.py
|   |   |   |   |-- production.py
|   |   |   |   |-- quality.py
|   |   |   |   |-- simulation.py
|   |   |   |   `-- traceability.py
|   |   |   |-- __init__.py
|   |   |   |-- deps.py
|   |   |   |-- errors.py
|   |   |   |-- request_id.py
|   |   |   `-- router.py
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- clock.py
|   |   |   |-- config.py
|   |   |   |-- database.py
|   |   |   |-- exceptions.py
|   |   |   |-- logging.py
|   |   |   |-- security.py
|   |   |   `-- throttle.py
|   |   |-- domain/
|   |   |   |-- __init__.py
|   |   |   |-- quality_rules.py
|   |   |   `-- state_machines.py
|   |   |-- investigation/
|   |   |   |-- __init__.py
|   |   |   |-- engine.py
|   |   |   |-- rules.py
|   |   |   `-- summary.py
|   |   |-- jobs/
|   |   |   |-- __init__.py
|   |   |   `-- check_overdue_orders.py
|   |   |-- models/
|   |   |   |-- __init__.py
|   |   |   |-- base_mixins.py
|   |   |   |-- enums.py
|   |   |   |-- investigation.py
|   |   |   |-- machine.py
|   |   |   |-- material.py
|   |   |   |-- product.py
|   |   |   |-- production.py
|   |   |   |-- quality.py
|   |   |   `-- user.py
|   |   |-- repositories/
|   |   |   |-- __init__.py
|   |   |   |-- pagination.py
|   |   |   |-- query_runner.py
|   |   |   `-- sql_loader.py
|   |   |-- schemas/
|   |   |   |-- __init__.py
|   |   |   |-- analytics.py
|   |   |   |-- auth.py
|   |   |   |-- catalog.py
|   |   |   |-- common.py
|   |   |   |-- investigation.py
|   |   |   |-- production.py
|   |   |   |-- quality.py
|   |   |   |-- simulation.py
|   |   |   `-- traceability.py
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- alert_service.py
|   |   |   |-- analytics_service.py
|   |   |   |-- auth_service.py
|   |   |   |-- catalog_service.py
|   |   |   |-- inspection_csv.py
|   |   |   |-- inspection_import.py
|   |   |   |-- investigation_service.py
|   |   |   |-- production_service.py
|   |   |   |-- quality_service.py
|   |   |   |-- simulation_service.py
|   |   |   `-- traceability_service.py
|   |   |-- simulation/
|   |   |   |-- __init__.py
|   |   |   |-- config.py
|   |   |   |-- engine.py
|   |   |   |-- events.py
|   |   |   |-- faults.py
|   |   |   |-- machine_state.py
|   |   |   `-- measurement.py
|   |   |-- __init__.py
|   |   |-- main.py
|   |   `-- seed.py
|   |-- migrations/
|   |   |-- versions/
|   |   |   |-- 20261104_0106_create_manufacturing_schema.py
|   |   |   `-- 20261107_2106_link_alerts_to_production_orders.py
|   |   |-- env.py
|   |   `-- script.py.mako
|   |-- tests/
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- test_alert_checks_api.py
|   |   |   |-- test_analytics_api.py
|   |   |   |-- test_auth_and_errors.py
|   |   |   |-- test_batches_api.py
|   |   |   |-- test_inspection_import.py
|   |   |   |-- test_investigations_api.py
|   |   |   |-- test_login_throttle_api.py
|   |   |   |-- test_machines_api.py
|   |   |   |-- test_orders_api.py
|   |   |   |-- test_pagination_api.py
|   |   |   |-- test_quality_api.py
|   |   |   |-- test_simulation_api.py
|   |   |   `-- test_traceability_api.py
|   |   |-- integration/
|   |   |   |-- __init__.py
|   |   |   |-- test_alert_order_link.py
|   |   |   |-- test_queries.py
|   |   |   |-- test_simulation_persistence.py
|   |   |   `-- test_transactions.py
|   |   |-- unit/
|   |   |   |-- __init__.py
|   |   |   |-- test_alert_rules.py
|   |   |   |-- test_inspection_csv.py
|   |   |   |-- test_investigation_rules.py
|   |   |   |-- test_login_throttle.py
|   |   |   |-- test_quality_rules.py
|   |   |   |-- test_security_and_loader.py
|   |   |   |-- test_simulation_engine.py
|   |   |   `-- test_state_machines.py
|   |   |-- __init__.py
|   |   `-- conftest.py
|   |-- alembic.ini
|   |-- pyproject.toml
|   |-- README.md
|   `-- uv.lock
|-- database/
|   |-- documentation/
|   |   `-- README.md
|   |-- queries/
|   |   |-- investigation/
|   |   |   |-- defect_onset.sql
|   |   |   |-- hourly_defect_rates.sql
|   |   |   |-- machine_events_before_onset.sql
|   |   |   `-- shared_material_lots.sql
|   |   |-- 01_machine_defect_rate_comparison.sql
|   |   |-- 02_production_performance.sql
|   |   |-- 03_recurring_defects.sql
|   |   |-- 04_material_lot_forward_trace.sql
|   |   |-- 05_unit_backward_trace.sql
|   |   |-- 06_quality_after_machine_events.sql
|   |   |-- 07_order_completion_summary.sql
|   |   |-- 08_batches_requiring_review.sql
|   |   |-- 09_daily_production_trend.sql
|   |   `-- 10_characteristic_control_chart.sql
|   |-- schema/
|   |   `-- schema.sql
|   `-- seeds/
|       |-- 01_reference_data.sql
|       |-- demo_scenario.json
|       `-- sample_inspection_import.csv
|-- docs/
|   |-- ai_evidence/
|   |   |-- conversations/
|   |   |   |-- 01-schema-and-normalization.md
|   |   |   |-- 02-simulation-state-machine-revision.md
|   |   |   |-- 03-migration-downgrade-rejected.md
|   |   |   |-- 04-quality-summary-orm-bug.md
|   |   |   `-- 05-environment-and-client-defaults.md
|   |   |-- ai-use-record.md
|   |   |-- README.md
|   |   `-- reflection-notes.md
|   |-- api/
|   |   `-- openapi.json
|   |-- architecture/
|   |   |-- component-design.md
|   |   |-- data-flow.md
|   |   |-- repository-structure.md
|   |   `-- system-overview.md
|   |-- database/
|   |   |-- data-dictionary.md
|   |   |-- database-design.md
|   |   |-- normalization.md
|   |   |-- queries.md
|   |   `-- seed-data.md
|   |-- decisions/
|   |   |-- ADR-0001-modular-monolith.md
|   |   |-- ADR-0002-mysql-as-system-of-record.md
|   |   |-- ADR-0003-alembic-single-migration-system.md
|   |   |-- ADR-0004-sql-files-as-runtime-and-documentation-source.md
|   |   |-- ADR-0005-rule-based-investigation-before-ml.md
|   |   |-- ADR-0006-deterministic-simulation-engine.md
|   |   |-- ADR-0007-jwt-roles-and-least-privilege-db-user.md
|   |   |-- ADR-0008-uv-and-pnpm-toolchains.md
|   |   |-- ADR-0009-cusum-onset-rule.md
|   |   `-- README.md
|   |-- development/
|   |   |-- coding-standards.md
|   |   |-- development-roadmap.md
|   |   `-- setup-guide.md
|   |-- investigation/
|   |   |-- investigation-engine.md
|   |   `-- traceability-design.md
|   |-- media/
|   |   |-- diagrams/
|   |   |   |-- backend-components.mmd
|   |   |   |-- backend-components.svg
|   |   |   |-- er-diagram.mmd
|   |   |   |-- er-diagram.svg
|   |   |   |-- investigation-workflow.mmd
|   |   |   |-- investigation-workflow.svg
|   |   |   |-- local-deployment.mmd
|   |   |   |-- local-deployment.svg
|   |   |   |-- manufacturing-workflow.mmd
|   |   |   |-- manufacturing-workflow.svg
|   |   |   |-- simulation-event-flow.mmd
|   |   |   |-- simulation-event-flow.svg
|   |   |   |-- system-architecture.mmd
|   |   |   |-- system-architecture.svg
|   |   |   |-- traceability-relationships.mmd
|   |   |   `-- traceability-relationships.svg
|   |   |-- screenshots/
|   |   |   |-- 01-login.png
|   |   |   |-- 02-overview-dashboard.png
|   |   |   |-- 03-machines-events.png
|   |   |   |-- 04-orders-and-batches.png
|   |   |   |-- 05-quality-inspections.png
|   |   |   |-- 06-investigation-case-board.png
|   |   |   |-- 07-traceability-and-quarantine.png
|   |   |   |-- 08-analytics-charts.png
|   |   |   |-- 09-analytics-sql-explorer.png
|   |   |   `-- README.md
|   |   |-- videos/
|   |   |   `-- README.md
|   |   `-- media-plan.md
|   |-- milestones/
|   |   |-- figures/
|   |   |   `-- week08-proposal-1.png
|   |   |-- build_documents.py
|   |   |-- html_pdf.py
|   |   |-- README.md
|   |   |-- week08-milestone-report.docx
|   |   |-- week08-milestone-report.md
|   |   |-- week08-milestone-report.pdf
|   |   |-- week08-proposal.docx
|   |   |-- week08-proposal.md
|   |   |-- week08-proposal.pdf
|   |   |-- week09-milestone-report.docx
|   |   |-- week09-milestone-report.md
|   |   |-- week09-milestone-report.pdf
|   |   |-- week10-milestone-report.docx
|   |   |-- week10-milestone-report.md
|   |   `-- week10-milestone-report.pdf
|   |-- quality/
|   |   `-- inspection-import.md
|   |-- requirements/
|   |   |-- business-rules.md
|   |   |-- functional-requirements.md
|   |   `-- non-functional-requirements.md
|   |-- simulation/
|   |   |-- fault-models.md
|   |   `-- simulation-design.md
|   `-- testing/
|       |-- test-matrix.md
|       `-- testing-strategy.md
|-- frontend/
|   |-- e2e/
|   |   |-- support/
|   |   |   |-- auth.ts
|   |   |   `-- env.ts
|   |   |-- analytics.spec.ts
|   |   |-- investigation.spec.ts
|   |   |-- login.spec.ts
|   |   |-- README.md
|   |   |-- roles.spec.ts
|   |   `-- traceability.spec.ts
|   |-- public/
|   |   `-- favicon.svg
|   |-- src/
|   |   |-- app/
|   |   |   |-- AppLayout.tsx
|   |   |   |-- nav.ts
|   |   |   |-- providers.tsx
|   |   |   |-- queryClient.ts
|   |   |   |-- RequireAuth.tsx
|   |   |   |-- router.tsx
|   |   |   `-- Sidebar.tsx
|   |   |-- components/
|   |   |   |-- charts/
|   |   |   |   |-- ChartFrame.test.tsx
|   |   |   |   |-- ChartFrame.tsx
|   |   |   |   |-- ControlChart.test.tsx
|   |   |   |   |-- ControlChart.tsx
|   |   |   |   |-- CountBarChart.tsx
|   |   |   |   |-- DailyTrendChart.tsx
|   |   |   |   `-- DefectRateChart.tsx
|   |   |   `-- ui/
|   |   |       |-- Button.tsx
|   |   |       |-- Chip.tsx
|   |   |       |-- DataTable.tsx
|   |   |       |-- Disclosure.tsx
|   |   |       |-- Field.tsx
|   |   |       |-- PageHeader.tsx
|   |   |       |-- Pagination.test.tsx
|   |   |       |-- Pagination.tsx
|   |   |       |-- Panel.tsx
|   |   |       |-- SqlDisclosure.test.tsx
|   |   |       |-- SqlDisclosure.tsx
|   |   |       |-- States.tsx
|   |   |       |-- StatTile.tsx
|   |   |       `-- StatusBadge.tsx
|   |   |-- features/
|   |   |   |-- analytics/
|   |   |   |   |-- AnalyticsPage.tsx
|   |   |   |   |-- ControlChartPanel.test.tsx
|   |   |   |   |-- ControlChartPanel.tsx
|   |   |   |   |-- SqlExplorer.test.tsx
|   |   |   |   |-- SqlExplorer.tsx
|   |   |   |   `-- WindowControls.tsx
|   |   |   |-- batches/
|   |   |   |   |-- BatchActions.tsx
|   |   |   |   |-- BatchesPage.tsx
|   |   |   |   `-- BatchForm.tsx
|   |   |   |-- investigations/
|   |   |   |   |-- CaseSummary.tsx
|   |   |   |   |-- EvidenceCard.test.tsx
|   |   |   |   |-- EvidenceCard.tsx
|   |   |   |   |-- FlaggedBatches.tsx
|   |   |   |   |-- InvestigationDetailPage.tsx
|   |   |   |   |-- InvestigationsPage.tsx
|   |   |   |   |-- OpenInvestigationForm.tsx
|   |   |   |   `-- StatusActions.tsx
|   |   |   |-- login/
|   |   |   |   |-- LoginPage.test.tsx
|   |   |   |   `-- LoginPage.tsx
|   |   |   |-- machines/
|   |   |   |   |-- EventTimeline.tsx
|   |   |   |   |-- MachineEventsPanel.tsx
|   |   |   |   |-- MachinesPage.tsx
|   |   |   |   `-- MachineStatusForm.tsx
|   |   |   |-- orders/
|   |   |   |   |-- OrderForm.tsx
|   |   |   |   |-- OrdersPage.test.tsx
|   |   |   |   |-- OrdersPage.tsx
|   |   |   |   `-- OrderTransitions.tsx
|   |   |   |-- overview/
|   |   |   |   |-- AlertsList.tsx
|   |   |   |   |-- MachineStatusCard.tsx
|   |   |   |   |-- OverviewPage.test.tsx
|   |   |   |   `-- OverviewPage.tsx
|   |   |   |-- quality/
|   |   |   |   |-- ImportInspectionsPanel.test.tsx
|   |   |   |   |-- ImportInspectionsPanel.tsx
|   |   |   |   |-- InspectionForm.tsx
|   |   |   |   |-- InspectionsPage.tsx
|   |   |   |   `-- useImportInspections.ts
|   |   |   |-- simulation/
|   |   |   |   |-- FaultScenarioBuilder.tsx
|   |   |   |   `-- SimulationPage.tsx
|   |   |   `-- traceability/
|   |   |       |-- QuarantineLotForm.tsx
|   |   |       |-- TraceabilityPage.test.tsx
|   |   |       |-- TraceabilityPage.tsx
|   |   |       `-- TraceSearchForm.tsx
|   |   |-- hooks/
|   |   |   |-- AuthProvider.test.tsx
|   |   |   |-- AuthProvider.tsx
|   |   |   |-- invalidate.ts
|   |   |   |-- queries.ts
|   |   |   |-- useAuth.ts
|   |   |   |-- useMediaQuery.ts
|   |   |   `-- usePageState.ts
|   |   |-- services/
|   |   |   |-- api.ts
|   |   |   |-- http.test.ts
|   |   |   `-- http.ts
|   |   |-- styles/
|   |   |   `-- index.css
|   |   |-- types/
|   |   |   |-- api.ts
|   |   |   `-- constants.ts
|   |   |-- utils/
|   |   |   |-- chartTheme.ts
|   |   |   |-- chartTransforms.test.ts
|   |   |   |-- chartTransforms.ts
|   |   |   |-- errors.ts
|   |   |   |-- format.ts
|   |   |   |-- permissions.test.ts
|   |   |   |-- permissions.ts
|   |   |   |-- renderCell.test.tsx
|   |   |   |-- renderCell.tsx
|   |   |   |-- statusTone.ts
|   |   |   |-- transitions.test.ts
|   |   |   `-- transitions.ts
|   |   `-- main.tsx
|   |-- tests/
|   |   |-- fixtures/
|   |   |   `-- controlChart.ts
|   |   |-- helpers.tsx
|   |   `-- setup.ts
|   |-- .gitignore
|   |-- .prettierignore
|   |-- .prettierrc
|   |-- eslint.config.js
|   |-- index.html
|   |-- package.json
|   |-- playwright.config.ts
|   |-- pnpm-lock.yaml
|   |-- README.md
|   |-- tsconfig.app.json
|   |-- tsconfig.e2e.json
|   |-- tsconfig.json
|   |-- tsconfig.node.json
|   `-- vite.config.ts
|-- scripts/
|   |-- development/
|   |   |-- benchmark_simulation.py
|   |   |-- capture_screenshots.py
|   |   |-- export_openapi.py
|   |   |-- export_schema.sh
|   |   |-- local_mysql.sh
|   |   |-- render_diagrams.py
|   |   |-- render_milestone_figures.py
|   |   `-- reset_database.py
|   `-- setup/
|       `-- init_databases.sh
|-- .editorconfig
|-- .env.example
|-- .gitignore
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- docker-compose.yml
|-- LICENSE
|-- Makefile
|-- README.md
`-- SECURITY.md
```

## Root files

| Path | Purpose | Status |
|------|---------|--------|
| `.editorconfig` | Editor defaults: UTF-8, LF, final newline, 2-space indent (4 for Python and SQL, tabs for Makefile), Python line length 100 | Implemented |
| `.env` | Local configuration read by the backend, Alembic, and the shell scripts. Ignored by Git. In this checkout `MYSQL_PORT=3307` | Implemented (local only) |
| `.env.example` | Template with placeholders for `MYSQL_*`, `MYSQL_ROOT_PASSWORD`, `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_MINUTES`, `LOGIN_MAX_FAILURES` (5), `LOGIN_WINDOW_SECONDS` (900), `SEED_DEMO_PASSWORD`, `CORS_ORIGINS`, `APP_ENV`, `LOG_LEVEL`; ships with `MYSQL_PORT=3306` | Implemented |
| `.gitignore` | Excludes `.env*` (except the example), Python caches and `.venv`, Node `node_modules`, frontend build output, `frontend/playwright-report/` and `frontend/test-results/`, `.local/` (local MySQL data), editor files | Implemented |
| `CHANGELOG.md` | Keep a Changelog format; only an Unreleased section exists | Implemented |
| `CONTRIBUTING.md` | Branch naming, Conventional Commits, quality gates, pull request process | Implemented |
| `docker-compose.yml` | Optional `mysql:8.4` service with `utf8mb4`, strict SQL mode, a `mysql-data` volume, a health check, and `scripts/setup/init_databases.sh` mounted as `/docker-entrypoint-initdb.d/01_init.sh` with `MYSQL_ROOT_ARGS` and `MYSQL_CLIENT_ARGS` set for the entrypoint's socket-only server | Written; executed only by the `compose-smoke.yml` workflow in CI (Docker is not installed on the development machine) |
| `LICENSE` | MIT | Implemented |
| `Makefile` | Wraps the development commands: `db-init`, `db-start`, `db-stop`, `migrate`, `seed`, `seed-demo`, `reset-demo`, `check-overdue`, `backend`, `frontend`, `test-backend`, `test-frontend`, `benchmark-sim`, `lint`, `format`, `export-schema`, `export-openapi`, `render-diagrams`, `render-figures`, `check-docs` | Implemented |
| `README.md` | Project entry point for the repository | Implemented |
| `SECURITY.md` | Reporting policy and known limitations; contact address placeholder to be filled by the owner | Implemented |

## backend/

### Toolchain files

| Path | Purpose | Status |
|------|---------|--------|
| `backend/pyproject.toml` | Project metadata, runtime dependencies (FastAPI, uvicorn, SQLAlchemy 2, Alembic, PyMySQL, cryptography, Pydantic with email, pydantic-settings, PyJWT, bcrypt, python-multipart), `dev` group (pytest, pytest-cov, httpx, ruff, mypy, types-pymysql), `docs` group (playwright, pillow, pypdf, python-docx, reportlab; used by `make render-diagrams`, `make render-figures`, the screenshot script, and `docs/milestones/build_documents.py`), hatchling build, Ruff and mypy configuration, pytest `integration` marker | Implemented |
| `backend/uv.lock` | Resolved dependency lock for `uv sync --locked` | Implemented |
| `backend/alembic.ini` | Alembic script location `migrations`, timestamped file template, logging; no credentials (URL injected by `env.py`) | Implemented |
| `backend/README.md` | Quick commands for the backend, with a link to the repository root README | Implemented |

### backend/app/main.py

- Purpose: FastAPI application factory and the `app` object uvicorn serves.
- Responsibilities: read settings, configure JSON logging, build the `FastAPI` instance (docs at `/api/docs`, OpenAPI at `/api/openapi.json`; both are disabled when `APP_ENV` is `production`), add `CORSMiddleware`, register `request_id_middleware`, register error handlers, mount `api_router`.
- Main functions: `create_app() -> FastAPI`; module-level `app`.
- Inputs: `Settings` via `get_settings()`.
- Outputs: configured application.
- Dependencies: `app.api.errors`, `app.api.request_id`, `app.api.router`, `app.core.config`, `app.core.logging`, `app.schemas.common.ErrorResponse`.
- Error schemas: `api_router` is included with `responses=` for 422, 500, and 503, and `app/api/router.py` adds 401, 403, 404, and 409 to the protected route modules (all `ErrorResponse`; the auth router gets 401 only and the health router none), so the protected routes in `docs/api/openapi.json` carry those error bodies.
- Related: `scripts/development/export_openapi.py` imports `app` to export the OpenAPI document.
- Error handling: delegated to `register_error_handlers`.
- Testing: covered indirectly by every API test through `TestClient(app)` in `tests/conftest.py`.
- Status: Implemented.

### backend/app/seed.py

- Purpose: command-line seeding (`uv run python -m app.seed [--demo]`).
- Responsibilities: execute `database/seeds/01_reference_data.sql` statement by statement (comment lines stripped first), create or refresh the four demo accounts with `SEED_DEMO_PASSWORD`, optionally run `database/seeds/demo_scenario.json` through `simulation_service.run_simulation`; one commit at the end.
- Main functions: `apply_reference_sql(session)`, `ensure_demo_users(session, password)`, `run_demo_scenario(session)`, `main(argv)`.
- Inputs: seed files, settings, `--demo` flag.
- Outputs: reference rows, `users` rows, optionally a full simulated history; exit code 2 when `SEED_DEMO_PASSWORD` is unset.
- Dependencies: `app.core.config`, `app.core.database`, `app.core.security`, `app.models`, `app.schemas.simulation`, `app.services.simulation_service`.
- Related: `scripts/development/reset_database.py` runs it as a subprocess; `tests/conftest.py` reuses `apply_reference_sql` and `ensure_demo_users`.
- Error handling: any exception rolls back the session and re-raises.
- Testing: exercised by the `db_session` fixture in every API and integration test.
- Status: Implemented.

### backend/app/core/

`__init__.py` is empty.

#### clock.py

- Purpose: single source of "now" for the services.
- Main function: `now()` returns `datetime.now()` with microseconds set to zero. MySQL `DATETIME` columns here have no fractional seconds, so truncating before the write keeps the value returned by a create call identical to the value read later.
- Related: imported by `analytics_service`, `catalog_service`, `investigation_service`, `production_service`, `quality_service`, and `traceability_service`. `routes/analytics.py` also imports it to build the default query window. Outside `clock.py`, `datetime.now` remains only in `core/logging.py` and `core/security.py`, which use UTC.
- Testing: covered indirectly, for example by `tests/api/test_analytics_api.py::test_alerts_can_be_acknowledged_once_by_operators`, which compares repeated acknowledgement timestamps.
- Status: Implemented.

#### config.py

- Purpose: single source of configuration.
- Responsibilities: load environment variables and the repository root `.env` (overridable by a local `.env`), expose typed settings and computed fields.
- Main symbols: `Settings` (fields `app_env`, `log_level`, `mysql_*`, `jwt_*`, `login_max_failures` (default 5, at least 1), `login_window_seconds` (default 900, at least 1), `seed_demo_password`, `cors_origins`; computed `effective_database`, `database_url`, `cors_origin_list`), `get_settings()` (cached).
- Inputs: environment, `.env`.
- Outputs: `Settings` instance.
- Dependencies: `pydantic`, `pydantic_settings`.
- Related: `app.core.database`, `app.core.security`, `migrations/env.py`, `scripts/development/reset_database.py`.
- Error handling: Pydantic validation errors at startup for malformed values; secrets are `repr=False`.
- Testing: `tests/conftest.py` sets `APP_ENV=test` before import and asserts the effective database ends with `_test`.
- Status: Implemented.

#### database.py

- Purpose: engine, session factory, declarative base, request-scoped session.
- Main symbols: `Base`, `build_engine()`, `engine`, `SessionLocal` (`autoflush=False`, `expire_on_commit=False`), `get_db_session()` generator (commit on success, rollback on exception, always close).
- Inputs: `Settings.database_url`.
- Outputs: `Session` objects for dependency injection.
- Dependencies: SQLAlchemy, `app.core.config`.
- Related: `app.api.deps.DbSession`, every model module (imports `Base`), `app.seed`, `tests/conftest.py`.
- Error handling: `pool_pre_ping=True` to survive idle connection drops; transaction rollback is the error path.
- Testing: `tests/integration/test_transactions.py::test_session_rolls_back_partial_writes` and `tests/api/test_batches_api.py::test_batch_with_unavailable_lot_leaves_nothing_behind`.
- Status: Implemented.

#### exceptions.py

- Purpose: typed application errors free of HTTP concerns.
- Main symbols: `AppError` (400, `message`, `details`), `NotFoundError` (404), `ConflictError` (409), `ValidationError` (422), `InvalidTransitionError` (subclass of `ValidationError`), `AuthenticationError` (401), `AuthorizationError` (403), `RateLimitedError` (429; takes `retry_after_seconds`, which it stores both as an attribute and in `details`).
- Dependencies: none.
- Related: raised by services, state machines, security, throttle, deps; mapped by `app.api.errors`.
- Testing: `tests/api/test_auth_and_errors.py` (`test_not_found_is_safe`, `test_validation_errors_name_the_field`), `tests/api/test_login_throttle_api.py::test_sixth_attempt_returns_429_with_retry_after`.
- Status: Implemented.

#### logging.py

- Purpose: single-line JSON logging.
- Main symbols: `JsonFormatter` (timestamp, level, logger, message, optional `request_id`, `user_id`, `operation`, exception text), `configure_logging(level)` (root and uvicorn loggers).
- Inputs: `LOG_LEVEL`.
- Related: `app.main`, `app.seed`, services that log with `extra`.
- Error handling: not applicable.
- Testing: no dedicated test.
- Status: Implemented.

#### security.py

- Purpose: password hashing and JWT issue and verification.
- Main functions: `hash_password`, `verify_password` (returns `False` on malformed hash), `create_access_token(user_id, role)` (HS256, `sub`, `role`, `iat`, `exp`), `decode_access_token(token)`.
- Inputs: plain passwords, hashes, tokens, `Settings.jwt_*`.
- Outputs: hashes, tokens, decoded payloads.
- Dependencies: `bcrypt`, `pyjwt`, `app.core.config`, `app.core.exceptions`.
- Related: `app.services.auth_service`, `app.api.deps`, `app.seed`.
- Error handling: `AuthenticationError` for expired or invalid tokens; `RuntimeError` when the secret is missing.
- Testing: `tests/unit/test_security_and_loader.py` (`test_password_hashes_are_salted_and_verifiable`, `test_tokens_round_trip_and_reject_tampering`).
- Status: Implemented.

#### throttle.py

- Purpose: slow down password guessing on `POST /auth/login`.
- Main symbols: `LoginThrottle(max_failures, window_seconds)` with `check(username, client_ip)`, `record_failure`, `record_success(username)`, `reset`, `tracked_keys`; `get_login_throttle()` (cached, built from `Settings.login_max_failures` and `login_window_seconds`).
- Behaviour: failures are appended as timestamps to one deque per lower-cased username and one per client address, under a `threading.Lock`; `check` prunes stamps older than the window and raises `RateLimitedError` with the seconds until the oldest stamp of the worst key expires when either key holds `max_failures` stamps; `record_success` drops the username's deque but keeps the address's. The store is one dictionary per API process.
- Inputs: username, client address, `clock.now()`.
- Dependencies: `app.core.clock`, `app.core.config`, `app.core.exceptions`.
- Related: `auth_service.authenticate` calls `check` before the user lookup and `record_failure` or `record_success` after the password check; `tests/conftest.py` resets the throttle around every test (`clean_login_throttle`, autouse).
- Error handling: `ValueError` when either limit is below 1; logs `login throttled` with `retry_after_seconds`.
- Testing: `tests/unit/test_login_throttle.py` (9 tests with a pinned clock, for example `test_fifth_failure_is_allowed_and_sixth_attempt_is_rejected`, `test_success_clears_the_username_but_not_the_address`, `test_expired_entries_are_pruned_on_every_call`), `tests/api/test_login_throttle_api.py` (6 tests through the endpoint).
- Status: Implemented.

### backend/app/api/

`__init__.py` and `routes/__init__.py` are empty.

#### router.py

- Purpose: compose the versioned API.
- Main symbol: `api_router` with prefix `/api/v1`, including health, auth, catalog, production, quality, investigations, traceability, analytics, simulation.
- Status: Implemented.

#### deps.py

- Purpose: FastAPI dependencies.
- Main symbols: `DbSession` (declared with `scope="function"` so the session closes, and commits, before the response is sent), `get_current_user` (bearer token to `User` via `auth_service.get_active_user`), `CurrentUser`, role sets `READ_ROLES`, `OPERATOR_ROLES`, `ENGINEER_ROLES`, `require_roles(allowed)`, `Operator`, `Engineer`, `get_page_params(limit, offset)` (`limit` 1 to 500, default 50; `offset` at least 0, default 0) and `Paging`.
- Inputs: `Authorization` header, session, `limit` and `offset` query parameters.
- Outputs: `User`, `PageParams`, or typed errors.
- Dependencies: `app.core.database`, `app.core.exceptions`, `app.core.security`, `app.models`, `app.repositories.pagination`, `app.services.auth_service`.
- Error handling: `AuthenticationError` when the header is missing, the token is invalid, or the user is inactive; `AuthorizationError` with `details.required` when the role is not allowed; FastAPI returns 422 for paging values outside the allowed ranges.
- Testing: `tests/api/test_auth_and_errors.py` (`test_requests_without_token_are_rejected`, `test_tampered_token_is_rejected`, `test_viewer_cannot_mutate`, `test_operator_cannot_create_products_but_can_read`, `test_me_reflects_database_role`), `tests/api/test_pagination_api.py` (`test_list_endpoints_default_to_limit_50_and_offset_0`, `test_invalid_paging_values_are_rejected`).
- Status: Implemented. ADMIN is a member of every write set; no route is admin-only, so there is no separate admin guard.

#### request_id.py

- Purpose: give every request an identifier that clients and logs can quote.
- Main symbols: `REQUEST_ID_HEADER` (`X-Request-ID`), `request_id_middleware` (stores the first 12 hex characters of a UUID4 in `request.state.request_id` and sets the response header), `request_id_of(request)` (returns `"unknown"` when none is set).
- Related: registered in `app.main`; read by `app.api.errors`.
- Testing: `tests/api/test_auth_and_errors.py::test_every_error_carries_a_request_id_header_and_field`.
- Status: Implemented.

#### errors.py

- Purpose: translate exceptions into safe JSON responses.
- Main function: `register_error_handlers(app)` registering handlers for `AppError` (its own status; a `Retry-After` header is added for `RateLimitedError`), `RequestValidationError` (422, per-field list), `IntegrityError` (MySQL 1062 duplicate key to 409, 1452 foreign key violation to 422, anything else to 500), `OperationalError` (1205 lock wait timeout and 1213 deadlock to 409 with a retry message, anything else to 503), `Exception` (500). Response body: `{"error", "message", "details", "request_id"}`, with the id also in the `X-Request-ID` response header. The `ErrorResponse` schema in `schemas/common.py` (used for the OpenAPI error entries) declares the same four fields.
- Error handling: uses the request id assigned by `request_id_middleware` in every response and in the log lines it writes (every `AppError` is logged at INFO as `request rejected` with `request_id`, `operation`, `error`, and `status`; database and unexpected errors are logged with `exc_info`); never returns SQL or stack traces.
- Testing: `tests/api/test_auth_and_errors.py` (`test_not_found_is_safe`, `test_validation_errors_name_the_field`, `test_unknown_fields_are_rejected`, `test_every_error_carries_a_request_id_header_and_field`), `tests/api/test_machines_api.py::test_create_machine_and_reject_duplicate`, `tests/api/test_login_throttle_api.py::test_sixth_attempt_returns_429_with_retry_after`.
- Status: Implemented.

#### routes/health.py

- `GET /health`: executes `SELECT 1` and returns `{"status": "ok", "database": "ok"}`. Unauthenticated. Tested by `tests/api/test_auth_and_errors.py::test_health_round_trips_to_mysql`. Implemented.

#### routes/auth.py

- `POST /auth/login` (`LoginRequest` to `TokenResponse` with `expires_in_minutes`; declares a 429 `ErrorResponse`; `_client_ip` passes the direct peer address to `auth_service.authenticate` and ignores `X-Forwarded-For`), `GET /auth/me` (`UserRead`). Depends on `auth_service`, `app.core.config`. Tested by `test_auth_and_errors.py` (`test_login_rejects_bad_credentials_without_revealing_which_part`, `test_me_reflects_database_role`) and `test_login_throttle_api.py`. Implemented.

#### routes/catalog.py

- Products: `GET /products`, `POST /products` (Engineer), `GET /products/{id}`, `PATCH /products/{id}` (Engineer). Specifications: `GET /specifications` (flat `list[SpecificationListItem]` across products, built in the route from `catalog_service.list_specifications`). Machines: `GET /machines`, `POST /machines` (Engineer), `GET /machines/{id}`, `POST /machines/{id}/status` (Operator), `GET /machines/{id}/events?limit=&offset=` (`Page[MachineEventRead]`). Material lots: `GET /material-lots`, `POST /material-lots` (Engineer). `GET /defect-types`.
- Dependencies: `app.schemas.catalog`, `app.schemas.common.Page`, `app.services.catalog_service`.
- Testing: `tests/api/test_machines_api.py` (`test_create_machine_and_reject_duplicate`, `test_machine_status_change_needs_reason_and_operator_role`), `tests/api/test_auth_and_errors.py`, `tests/api/test_pagination_api.py`.
- Status: Implemented.

#### routes/production.py

- Orders: `GET /production-orders?status=&limit=&offset=` (`Page[ProductionOrderRead]`), `POST /production-orders` (Engineer), `GET /production-orders/{id}`, `PATCH /production-orders/{id}` (Engineer), `POST /production-orders/{id}/status` (Operator). Batches: `GET /production-batches?order_id=&machine_id=&limit=&offset=` (`Page[ProductionBatchRead]`), `POST /production-batches` (Operator), `GET /production-batches/{id}`, `POST /production-batches/{id}/complete` (Operator), `POST /production-batches/{id}/quarantine` (Engineer, via `traceability_service`).
- Dependencies: `app.schemas.production`, `app.schemas.common.Page`, `app.services.production_service`, `app.services.traceability_service`, `app.models.enums.OrderStatus`.
- Testing: `tests/api/test_orders_api.py` (6 tests), `tests/api/test_batches_api.py` (9 tests including `test_batch_creation_writes_batch_units_and_materials_together`, `test_completing_batches_completes_the_order`, `test_quarantine_batch_records_reason_and_alert`), `tests/api/test_pagination_api.py` (`test_pages_are_stable_disjoint_and_cover_every_order`, `test_status_filter_applies_before_paging`, `test_batch_and_inspection_filters_combine_with_paging`).
- Status: Implemented.

#### routes/quality.py

- `GET /inspections?batch_id=&result=&limit=&offset=` (`Page[InspectionRead]`, items built with `quality_service.to_read`), `POST /inspections` (Operator), `POST /inspections/import` (Operator; `file: UploadFile` from a multipart body, read up to `MAX_FILE_BYTES + 1` bytes and passed with its content type and file name to `inspection_import.import_csv`; 201 with `InspectionImportResult`; the OpenAPI description states the columns and limits), `GET /quality/summary?machine_id=&batch_id=`.
- Dependencies: `app.schemas.quality`, `app.schemas.common.Page`, `app.services.quality_service`, `app.services.inspection_import`, `app.services.inspection_csv.MAX_FILE_BYTES`.
- Testing: `tests/api/test_quality_api.py` (`test_measurement_is_validated_against_specification`, `test_inspection_rejects_bad_references`, and others), `tests/api/test_inspection_import.py` (16 tests).
- Status: Implemented.

#### routes/investigations.py

- `GET /investigations?limit=&offset=` (`Page[InvestigationRead]`), `POST /investigations` (Engineer, passes `user.id` as `opened_by`), `GET /investigations/{id}`, `POST /investigations/{id}/status` (Engineer).
- Dependencies: `app.schemas.investigation`, `app.schemas.common.Page`, `app.services.investigation_service`.
- Testing: `tests/api/test_investigations_api.py` (`test_high_defect_rate_is_detected_with_evidence` asserts the codes `R1` to `R7` in order, `test_healthy_machine_is_not_flagged`, `test_investigation_lifecycle_and_validation`, `test_evidence_rows_keep_sql_column_order`).
- Status: Implemented.

#### routes/traceability.py

- `GET /traceability/forward/{lot_number}` (`ForwardTraceRead`: `lot_number` plus `batches` as `ForwardTraceRow` items), `GET /traceability/backward/{serial_number}` (`BackwardTraceRead`: `serial_number` plus `lineage` as `BackwardTraceRow` items), `POST /traceability/material-lots/{lot_id}/quarantine` (Engineer; `LotQuarantineRead` with the lot and the newly quarantined batches).
- Dependencies: `app.services.traceability_service`, `app.services.catalog_service`, `app.schemas.traceability`, `app.schemas.catalog`, `app.schemas.production`.
- Testing: `tests/api/test_traceability_api.py` (`test_forward_and_backward_trace_agree`, `test_unknown_lot_and_serial_return_404`, `test_lot_quarantine_cascades_to_batches_in_one_transaction`).
- Status: Implemented.

#### routes/analytics.py

- `GET /analytics/queries` (`list[QueryCatalogEntry]`: all fourteen SQL files with name, header text, full SQL, `runnable` flag, and parameter names), `GET /analytics/queries/{name}` (`QueryResult`; runs one of the eight whitelisted dashboard queries (the other six return 422 with the runnable names in `details.runnable_queries`) with `window_start`, `window_end`, `machine_id`, `specification_id`, `threshold`, `hours`, `limit`; default window is the last 30 days to tomorrow), `GET /analytics/alerts?limit=&offset=` (`Page[AlertRead]`), `POST /analytics/alerts/{id}/acknowledge` (Operator guard: OPERATOR, ENGINEER, or ADMIN; a VIEWER receives 403), `POST /analytics/alerts/checks/overdue-orders` (Operator; optional `OverdueCheckRequest` body with `as_of`; returns `OverdueCheckResponse` with `checked`, `raised`, and the new alerts).
- Dependencies: `app.services.analytics_service`, `app.services.alert_service`, `app.schemas.analytics`, `app.schemas.common.Page`, `app.schemas.investigation.AlertRead`, `app.core.clock`.
- Error handling: an unknown query name raises `NotFoundError` (404) and a known but non-runnable one raises `ValidationError` (422), both in `analytics_service.run_dashboard_query`; an inverted window is also 422, and so is `characteristic_control_chart` without `specification_id`.
- Testing: `tests/api/test_analytics_api.py` (`test_query_catalog_lists_every_sql_file`, `test_dashboard_query_returns_sql_params_and_rows`, `test_only_dashboard_queries_are_exposed` (asserts the 422 and `runnable_queries`), `test_alerts_can_be_acknowledged_once_by_operators`, and others; 7 tests), `tests/api/test_alert_checks_api.py` (7 tests), `tests/integration/test_queries.py` (`test_all_queries_run_and_agree`).
- Status: Implemented.

#### routes/simulation.py

- `POST /simulation/runs` (Engineer): `SimulationRequest` to `SimulationResult`, status 201.
- Testing: `tests/api/test_simulation_api.py` (`test_simulation_persists_consistent_counts`, `test_simulation_is_deterministic_across_runs`, `test_simulation_validates_input`).
- Status: Implemented.

### backend/app/schemas/

`__init__.py` is empty. All request models use `extra="forbid"`; response models extend `ApiModel`.

| File | Main models | Notes | Status |
|------|-------------|-------|--------|
| `common.py` | `ApiModel`, `ErrorResponse` (`error`, `message`, `details`, `request_id`), `Page[T]` (`items`, `total`, `limit`, `offset`; `from_result(result, paging, convert)`) | `ErrorResponse` is attached to routes through `responses=` in `main.py` and `router.py`; `Page` imports `PageParams` and `PageResult` from `app.repositories.pagination` | Implemented |
| `analytics.py` | `QueryCatalogEntry` (`name`, `description`, `sql`, `runnable`, `parameters`), `QueryResult` (`query`, `sql`, `params`, `rows`), `OverdueCheckRequest` (optional `as_of`, `extra="forbid"`), `OverdueCheckResponse` (`checked`, `raised`, `alerts`) | `response_model` of the two analytics query endpoints and the overdue check | Implemented |
| `auth.py` | `LoginRequest`, `TokenResponse`, `UserRead` | `UserRead.email` is `EmailStr` | Implemented |
| `catalog.py` | `SpecificationCreate`, `SpecificationRead`, `SpecificationListItem` (adds `product_id` and `product_code`), `ProductCreate`, `ProductUpdate`, `ProductRead`, `MachineCreate`, `MachineRead`, `MachineStatusChange`, `MachineEventRead`, `DefectTypeRead`, `MaterialLotCreate`, `MaterialLotRead`; `CODE_PATTERN` | Decimal fields carry `decimal_places` limits; `CODE_PATTERN` is reused by `inspection_csv` for defect codes | Implemented |
| `production.py` | `ProductionOrderCreate`, `ProductionOrderUpdate`, `ProductionOrderStatusChange`, `ProductionOrderRead`, `BatchMaterialInput`, `BatchMaterialRead`, `ProductionBatchCreate` (at least one material), `ProductionBatchRead`, `QuarantineRequest` (reason 5 to 255 characters) | Quantity caps: orders 100,000, batches 10,000 | Implemented |
| `quality.py` | `InspectionCreate`, `InspectionRead` (with `defect_codes`), `QualitySummary`, `InspectionImportResult` (`imported`, `failed_inspections`, `inspection_ids`) | Result is never accepted from the client | Implemented |
| `traceability.py` | `ForwardTraceRow`, `ForwardTraceRead` (`lot_number`, `batches`), `BackwardTraceRow`, `BackwardTraceRead` (`serial_number`, `lineage`), `LotQuarantineRead` (`lot`, `quarantined_batches`) | Row models mirror the columns of queries 04 and 05 | Implemented |
| `investigation.py` | `InvestigationCreate`, `InvestigationStatusChange`, `EvidenceRead`, `InvestigationBatchRead`, `InvestigationRead`, `AlertRead` | `AlertRead` exposes `production_order_id` and omits `acknowledged_by`; `EvidenceRead` rebuilds ordered row dictionaries from the stored `{"columns", "rows"}` JSON with a `field_validator`, so the API still returns `result_rows` as a list of objects in SQL column order | Implemented |
| `simulation.py` | `FaultScenario`, `SimulationRequest` (seed default 42, limits 200 batches per machine, 500 units per batch, 600 minutes per batch), `SimulationResult` | Fault kind validated later by the service | Implemented |

Testing: schema validation behaviour is covered through the API tests (`test_unknown_fields_are_rejected`, `test_validation_errors_name_the_field`, `test_invalid_orders_are_rejected`, `test_simulation_validates_input`).

### backend/app/models/

`__init__.py` imports every model and enum so `Base.metadata` is complete; it re-exports them for the rest of the application.

| File | Tables / symbols | Key constraints and indexes | Status |
|------|------------------|-----------------------------|--------|
| `base_mixins.py` | `TimestampMixin` (`created_at`, `updated_at` with `func.now()` defaults) | Used by `Product`, `Machine`, `ProductionOrder` | Implemented |
| `enums.py` | `UserRole`, `MachineStatus`, `MachineEventType`, `Severity`, `OrderStatus`, `BatchStatus`, `MaterialLotStatus`, `InspectionResult`, `AlertType`, `InvestigationStatus` | Stored as MySQL `ENUM` | Implemented |
| `user.py` | `users` | unique `username`, `email`; `is_active` | Implemented |
| `product.py` | `products`, `product_specifications` | unique `code`; unique (`product_id`, `characteristic`); `tolerance > 0`; cascade delete of specifications | Implemented |
| `machine.py` | `machines`, `machine_events` | unique `code`; index (`machine_id`, `occurred_at`); events `RESTRICT` on machine delete | Implemented |
| `material.py` | `material_lots`, `batch_materials` (junction) | unique `lot_number`; `quantity_received >= 0`; `quantity_used > 0`; composite primary key | Implemented |
| `production.py` | `production_orders`, `production_batches`, `production_units` | quantity CHECKs; `ix_production_orders_status`; `ix_production_batches_machine_time`, `ix_production_batches_order`; unique `batch_number`, `serial_number`, (`batch_id`, `sequence_in_batch`) | Implemented. The `ProductionOrder` docstring points to `app.domain.state_machines` for legal status transitions |
| `quality.py` | `defect_types`, `inspections`, `inspection_defects` (junction) | unique (`unit_id`, `specification_id`); `ix_inspections_time_result`; `RESTRICT` on specification and defect type deletes | Implemented |
| `investigation.py` | `alerts`, `investigations`, `investigation_evidence`, `investigation_batches` (junction) | `alerts.machine_id` and `alerts.production_order_id` are nullable `SET NULL` references (the latter named `fk_alerts_production_order`, indexed by `ix_alerts_production_order`, added by the second migration); `ix_alerts_created` on (`created_at`, `id`); `window_end > window_start`; `(status = 'CLOSED') = (closed_at IS NOT NULL)`; unique (`investigation_id`, `sequence`); evidence `result_rows` as `JSON` holding `{"columns": [...], "rows": [[...]]}` (written by `investigation_service.evidence_payload`); cascade from investigation | Implemented |

Error handling: constraint violations surface as `IntegrityError` and are mapped to 409 or converted by `_flush_or_conflict`. Testing: `tests/integration/test_transactions.py` (`test_foreign_keys_are_enforced_by_mysql`, `test_check_and_enum_constraints_reject_bad_rows`), `tests/unit/test_state_machines.py::test_every_machine_state_has_a_row`. Column-level detail is in `docs/database/data-dictionary.md`.

### backend/app/domain/

`__init__.py` carries the package docstring (pure rules, no database or HTTP).

#### quality_rules.py

- Main symbols: defect code constants (`DEFECT_OVERSIZE`, `DEFECT_UNDERSIZE`, `DEFECT_HOLE_POSITION`, `DEFECT_DIMENSIONAL`, `DEFECT_SURFACE`), `DIAMETER_CHARACTERISTICS`, `Evaluation`, `evaluate_measurement(measured, target, tolerance, characteristic)`, `classify_defect(characteristic, deviation)`, `defect_rate(failed, inspected)`.
- Inputs: `Decimal` values and the characteristic name.
- Outputs: `Evaluation` (result, deviation, defect code) and rounded rates.
- Dependencies: `app.models.enums.InspectionResult`.
- Related: `quality_service.record_inspection`, `simulation.engine._inspect`, `investigation` (rates are computed in SQL there but with the same definition).
- Error handling: none; pure functions.
- Testing: `tests/unit/test_quality_rules.py` (`test_values_inside_tolerance_pass`, `test_diameter_failures_are_classified_by_direction`, `test_other_characteristics_map_to_their_defect_types`, `test_defect_rate_definition`).
- Status: Implemented.

#### state_machines.py

- Main symbols: `MACHINE_TRANSITIONS`, `ORDER_TRANSITIONS`, `BATCH_TRANSITIONS`, `INVESTIGATION_TRANSITIONS`, `assert_transition[S](table, current, target, entity=...)`.
- Outputs: raises `InvalidTransitionError` with `current`, `target`, `allowed` in `details`.
- Dependencies: `app.core.exceptions`, `app.models.enums`.
- Related: `catalog_service.change_machine_status`, `production_service.change_order_status`, `production_service.complete_batch`, `traceability_service.quarantine_batch`, `investigation_service.change_status`, `simulation.machine_state.MachineStateTracker`.
- Testing: `tests/unit/test_state_machines.py` (`test_legal_order_transitions`, `test_illegal_order_transitions_are_rejected`, `test_fault_must_go_through_stopped`, `test_every_machine_state_has_a_row`), `tests/api/test_orders_api.py::test_cancelled_order_cannot_start_production`.
- Status: Implemented. `QUARANTINED` is terminal; the comment on `BATCH_TRANSITIONS` states that re-inspected material is released by creating a new batch.

### backend/app/services/

`__init__.py` is empty. Every function takes a `Session` first and never commits.

#### auth_service.py

- `authenticate(session, *, username, password, client_ip) -> (User, token)`; `get_active_user(session, user_id)`; module constant `_UNKNOWN_USER_HASH`, a bcrypt hash compared against when the username does not exist so the request takes as long as a real check.
- Behaviour: `get_login_throttle().check` runs before the user lookup and the bcrypt check; a failure calls `record_failure`, a success calls `record_success`.
- Error handling: `RateLimitedError` (429) from the throttle; one `AuthenticationError("Invalid username or password")` for unknown user, inactive user, or wrong password; logs `login rejected` and `login accepted` with `operation`.
- Testing: `tests/api/test_auth_and_errors.py`, `tests/api/test_login_throttle_api.py` (`test_unknown_usernames_are_throttled_like_real_ones`, `test_success_resets_the_username_counter_but_not_the_address_counter`, and others).
- Status: Implemented.

#### catalog_service.py

- Functions: `_flush_or_conflict(session, what)` (turns `IntegrityError` on flush into `ConflictError`), product list, get, create (with nested specifications), update; `list_specifications` (every `ProductSpecification` with its product `joinedload`ed, ordered by product code then characteristic); machine list, get, create, `change_machine_status` (asserts transition, writes a `STATE_CHANGE` `MachineEvent` with `CRITICAL` severity when entering `FAULT`), `list_machine_events(session, machine_id, paging) -> PageResult[MachineEvent]` (404 for an unknown machine; ordered `occurred_at desc, id desc`); material lot list, get, create; `list_defect_types`.
- Dependencies: `app.domain.state_machines`, `app.models`, `app.repositories.pagination`, `app.schemas.catalog`, `app.core.exceptions`, `app.core.clock`.
- Related: `production_service` and `quality_service` import `_flush_or_conflict`; `investigation_service` and `traceability_service` use the getters; `routes/catalog.py` builds `SpecificationListItem` rows from `list_specifications`.
- Testing: `tests/api/test_machines_api.py`, `tests/api/test_machines_api.py::test_machine_state_transitions_are_enforced_and_logged`, `tests/api/test_pagination_api.py`.
- Status: Implemented.

#### production_service.py

- Constants: `EDITABLE_ORDER_STATES` (PLANNED, RELEASED), `PRODUCIBLE_ORDER_STATES` (RELEASED, IN_PROGRESS).
- Functions: `list_orders(session, paging, status=) -> PageResult` (ordered `created_at desc, id desc`), `get_order`, `create_order` (validates product and machine), `update_order` (only in editable states), `change_order_status` (release needs a machine; completion needs the planned quantity produced), `list_batches(session, paging, order_id=, machine_id=) -> PageResult` (ordered `started_at desc, id desc`), `get_batch`, `next_batch_number`, `create_batch` (see [data-flow.md](data-flow.md#production-batch-creation)), `complete_batch` (increments `quantity_completed` with an SQL `UPDATE`, completes the order when planned quantity is reached).
- Dependencies: `app.domain.state_machines`, `app.models`, `app.repositories.pagination`, `app.schemas.production`, `catalog_service`.
- Error handling: `NotFoundError`, `ValidationError`, `ConflictError`, `InvalidTransitionError`.
- Testing: `tests/api/test_orders_api.py`, `tests/api/test_batches_api.py`, `tests/api/test_pagination_api.py`, `tests/integration/test_transactions.py` (rollback of partial writes).
- Status: Implemented.

#### quality_service.py

- Functions: `record_inspection` (unit and specification must exist, specification must belong to the unit's product, result computed by `evaluate_measurement`, derived defect code merged with client codes, codes rejected on a passing inspection, unknown codes rejected, duplicate unit and specification pair becomes 409), `to_read`, `list_inspections(session, paging, batch_id=, result=) -> PageResult` (ordered `inspected_at desc, id desc`), `quality_summary` (produced, inspected, passed, failed, `defect_rate`).
- Dependencies: `app.domain.quality_rules`, `app.models`, `app.repositories.pagination`, `app.schemas.quality`, `catalog_service._flush_or_conflict`.
- Related: `inspection_import` calls `record_inspection` once per CSV row.
- Testing: `tests/api/test_quality_api.py` (3 tests), `tests/api/test_inspection_import.py`, `tests/api/test_pagination_api.py`.
- Status: Implemented.

#### inspection_csv.py

- Purpose: parse an inspection CSV into typed rows and collect every structural problem before the database is consulted.
- Constants: `REQUIRED_COLUMNS` (`serial_number`, `characteristic`, `measured_value`), `OPTIONAL_COLUMNS` (`inspected_at`, `defect_type_codes`), `MAX_FILE_BYTES` (1 MiB), `MAX_DATA_ROWS` (5000), `MAX_DEFECT_CODES` (10), `SERIAL_MAX_LENGTH` (40), `CHARACTERISTIC_MAX_LENGTH` (50), `MEASURED_MAX_ABS` (10,000,000).
- Main symbols: `RowError` (`row`, `field`, `message`; `row` is `None` for header and file problems), `ImportRow`, `FieldError`, `import_error(message, errors)` and `file_error(message)` (build the 422 `ValidationError` with `details.errors`), `parse_csv(text) -> (rows, errors)`, field parsers `_required_text`, `_parse_measured` (decimal, finite, three places, below the `NUMERIC(10, 3)` range), `_parse_timestamp` (ISO 8601 without offset, microseconds dropped), `_parse_codes` (`|` separated, `CODE_PATTERN`, de-duplicated, at most ten), `_duplicate_error`.
- Behaviour: header problems, an empty file, and the row limit raise immediately; row problems are collected so one upload reports everything; blank lines are skipped; column names are trimmed and lower-cased.
- Dependencies: `csv`, `decimal`, `app.core.exceptions`, `app.schemas.catalog.CODE_PATTERN`. No session, no logging.
- Testing: `tests/unit/test_inspection_csv.py` (14 tests, no MySQL).
- Status: Implemented.

#### inspection_import.py

- Purpose: import a CSV upload in one transaction through the manual entry rules.
- Main symbols: `ACCEPTED_CONTENT_TYPES` (`text/csv`, `application/csv`, `application/vnd.ms-excel`; `application/octet-stream` only with a `.csv` name), `import_csv(session, content, *, content_type, filename) -> InspectionImportResult`, `decode_upload` (content type, non-empty, size, `utf-8-sig`), `_Lookups`, `_load_lookups` (units by serial with product id through batch and order, all specifications keyed by product and lower-cased characteristic, defect codes, already inspected (`unit_id`, `specification_id`) pairs), `_resolve_rows`, `_resolve_row`, `_rule_errors` (existing inspection, unknown codes, codes on a passing value).
- Behaviour: every row error from the parser and the resolution is sorted by row and field and returned in one 422; otherwise each `InspectionCreate` is recorded through `quality_service.record_inspection`, and the result carries the count, the failed count, and the new ids. Nothing commits; logs `inspections imported` with the counts under `operation=inspections.import`.
- Dependencies: `app.core.clock`, `app.domain.quality_rules`, `app.models`, `app.schemas.quality`, `inspection_csv`, `quality_service`.
- Related: `routes/quality.import_inspections`; documented in `docs/quality/inspection-import.md`; sample file `database/seeds/sample_inspection_import.csv`.
- Testing: `tests/api/test_inspection_import.py` (16 tests including `test_one_invalid_row_rolls_back_the_whole_file`, `test_duplicate_against_the_database_is_rejected`, `test_non_csv_and_empty_uploads_are_rejected`, `test_sample_file_imports_against_the_demo_scenario`).
- Status: Implemented.

#### traceability_service.py

- Functions: `forward_trace(lot_number)` (404 if the lot does not exist, then query 04), `backward_trace(serial_number)` (query 05; 404 when no rows), `quarantine_batch(batch_id, reason)` (transition check, `MATERIAL_QUARANTINE` warning alert), `quarantine_lot(lot_id, reason)` (lot to `QUARANTINED`, every non-quarantined consuming batch to `QUARANTINED` with a prefixed reason, one `CRITICAL` alert; returns the batches changed).
- Dependencies: `app.repositories.query_runner`, `app.domain.state_machines`, `catalog_service`, `production_service`.
- Testing: `tests/api/test_traceability_api.py` (including `test_lot_quarantine_cascades_to_batches_in_one_transaction`), `tests/api/test_batches_api.py::test_quarantine_batch_records_reason_and_alert`.
- Status: Implemented.

#### investigation_service.py

- Functions: `list_investigations(session, paging) -> PageResult` (ordered `created_at desc, id desc`, evidence and batch links eager-loaded), `get_investigation` (eager-loads evidence and batch links), `open_investigation` (machine and product existence, `InvestigationContext`, `investigate`, persist investigation plus evidence plus batch links, reload; the window order is checked by `InvestigationCreate`'s validator), `evidence_payload(rows)` (stores rows as a column list plus value arrays because MySQL reorders JSON object keys), `change_status` (transition check; closing requires a conclusion and sets `closed_at`).
- Dependencies: `app.investigation.engine`, `app.investigation.rules`, `app.repositories.pagination`, `app.repositories.query_runner`, `app.domain.state_machines`, `catalog_service`.
- Testing: `tests/api/test_investigations_api.py`.
- Status: Implemented. `product_id` is stored but not used by the rules.

#### analytics_service.py

- Symbols: `DASHBOARD_QUERIES` (eight names with their permitted parameters: `machine_defect_rate_comparison`, `recurring_defects`, `daily_production_trend`, `order_completion_summary`, `production_performance`, `batches_requiring_review`, `quality_after_machine_events`, `characteristic_control_chart`), `run_dashboard_query` (returns `query`, `sql`, `params`, `rows`; raises `NotFoundError` for an unknown name and `ValidationError` for a known query outside `DASHBOARD_QUERIES`, for an inverted window, or for `characteristic_control_chart` without `specification_id`), `list_query_catalog` (all fourteen files as dictionaries with `name`, `description`, `sql`, `runnable`, `parameters`; the route wraps them in `QueryCatalogEntry`), `recent_alerts(session, paging) -> PageResult[Alert]` (ordered `created_at desc, id desc`), `acknowledge_alert` (idempotent; sets `acknowledged_at` from `app.core.clock.now()` and `acknowledged_by`).
- Dependencies: `app.repositories.sql_loader`, `app.repositories.query_runner`, `app.repositories.pagination`, `app.models.Alert`, `app.core.clock`.
- Testing: `tests/api/test_analytics_api.py`, `tests/api/test_pagination_api.py`, `tests/integration/test_queries.py`.
- Status: Implemented.

#### alert_service.py

- Purpose: the overdue order check, shared by `POST /analytics/alerts/checks/overdue-orders` and `app/jobs/check_overdue_orders.py`.
- Symbols: `OPEN_ORDER_STATES` (every `OrderStatus` except `COMPLETED` and `CANCELLED`), `CRITICAL_AFTER_DAYS` (2), `OverdueCheckResult` (`checked`, `raised`, `alerts`), `days_late(due_date, as_of)` (whole calendar days), `overdue_severity(days)` (`WARNING` up to two days, `CRITICAL` after), `overdue_message`, `_naive` (drops a UTC offset and microseconds), `overdue_orders(session, as_of)` (open orders with `due_date` before the check date, ordered by due date then id), `_orders_with_open_alert` (unacknowledged `ORDER_OVERDUE` alerts by `production_order_id`), `raise_overdue_order_alerts(session, as_of=None)`.
- Behaviour: one `Alert` per overdue order without an open overdue alert, with `machine_id`, `production_order_id`, severity by days late, and `created_at = as_of`; flushes, never commits.
- Dependencies: `app.core.clock`, `app.models`.
- Testing: `tests/unit/test_alert_rules.py` (5 tests, no MySQL), `tests/api/test_alert_checks_api.py` (7 tests), `tests/integration/test_alert_order_link.py` (3 tests).
- Status: Implemented.

#### simulation_service.py

- Symbols: `PRODUCT_MATERIALS` (product code to material name), `load_catalog` (products with specifications, machines, `AVAILABLE` lots grouped by material name, defect type ids; `ValidationError` when a product has no lot or the defect catalogue lacks a code the simulator produces), `to_config` (request to `SimulationConfig`; unknown fault kind becomes `ValidationError`), `run_simulation`, `_next_run_tag` (`SIMnnnn` from the count of production orders), `BULK_CHUNK_SIZE` (1000), `persist` (delegates to `_persist_orders`, `_persist_batches`, `_complete_orders`, `_unit_rows`, `_unit_ids_by_serial`, `_inspection_rows`, `_inspection_ids_by_unit_and_spec`, `_defect_rows`, `_event_rows`, `_persist_alerts`, and `_bulk_insert`; sets final machine statuses; returns `SimulationResult`).
- Behaviour: orders, batches with `COMPLETED` status and material links, and alerts are ORM objects; units, inspections, inspection defects, and machine events are chunked multi-row `INSERT`s, with unit ids selected back by serial number and inspection ids by (`unit_id`, `specification_id`) because MySQL returns no generated ids for a multi-row insert. See [data-flow.md](data-flow.md#simulation-run-persistence).
- Dependencies: `app.simulation.*`, `app.models`, `app.schemas.simulation`, `app.core.database.Base`, `app.domain.quality_rules.DEFECT_CODES`.
- Related: `scripts/development/benchmark_simulation.py` times `run_simulation` for two request shapes.
- Testing: `tests/api/test_simulation_api.py`, `tests/integration/test_simulation_persistence.py` (`test_run_spanning_several_chunks_persists_exact_counts`, `test_inspections_point_at_the_unit_with_the_matching_serial`), `tests/integration/test_transactions.py`, `tests/integration/test_queries.py` (uses the `simulated` fixture).
- Status: Implemented.

### backend/app/jobs/

`__init__.py` carries the package docstring: each module opens its own session, calls one service function, commits, and logs a JSON line.

#### check_overdue_orders.py

- Purpose: run the overdue order check from the command line or a scheduler (`uv run python -m app.jobs.check_overdue_orders [--as-of 2026-11-07T08:00:00]`, `make check-overdue`).
- Main function: `main(argv) -> int`: parses `--as-of` (ISO 8601, default now), calls `configure_logging`, opens `SessionLocal()`, calls `alert_service.raise_overdue_order_alerts`, commits, logs `overdue order check finished` with `{"checked", "raised", "alert_ids"}` under `operation=check_overdue_orders`, returns 0.
- Dependencies: `app.core.config`, `app.core.database`, `app.core.logging`, `app.services.alert_service`.
- Error handling: any exception rolls the session back and re-raises (non-zero exit).
- Testing: `tests/integration/test_alert_order_link.py::test_job_commits_and_exits_zero`.
- Status: Implemented. Nothing in the repository schedules it.

### backend/app/simulation/

`__init__.py` is empty.

| File | Main symbols | Inputs and outputs | Testing | Status |
|------|--------------|--------------------|---------|--------|
| `config.py` | `FaultKind`, `FaultScenario`, `SimulationConfig` (validates minimums in `__post_init__`), `SpecRef`, `ProductRef`, `MachineRef`, `Catalog` (validates non-empty products, machines, specs, lots) | Frozen inputs built by `simulation_service` | `tests/unit/test_simulation_engine.py::test_invalid_configuration_is_rejected` | Implemented |
| `engine.py` | `SimulationEngine` (`run`, `_run_machine`, `_make_order`, `_product_for`, `_inject_fault`, `_produce_batch`, `_inspect`), fault event type and description tables | `(SimulationConfig, Catalog)` to `SimulationOutput`; `ValueError` for faults on unknown machines | `test_same_seed_same_history`, `test_different_seed_different_measurements`, `test_counts_follow_configuration`, `test_tool_wear_raises_failures_and_leaves_machine_in_warning`, `test_downtime_skips_a_batch_and_cycles_states`, `test_unknown_fault_machine_is_rejected`, `test_normal_production_has_low_failure_rate` | Implemented |
| `faults.py` | `TOOL_WEAR_RATE`, `CALIBRATION_OFFSET`, `VARIATION_MULTIPLIER`, `MATERIAL_ISSUE_PROBABILITY`, `ActiveFault`, `MeasurementEffect`, `combined_effect` | Active faults to a combined effect per measurement | Covered through engine tests | Implemented |
| `measurement.py` | `NATURAL_SIGMA_FRACTION`, `MeasurementGenerator.generate(spec, effect) -> (Decimal, gross)` | Random draws quantised to 0.001 | Covered through engine tests | Implemented |
| `machine_state.py` | `MachineStateTracker.transition(target, at, reason)` | Appends `StateChange` records; enforces `MACHINE_TRANSITIONS` | `test_downtime_skips_a_batch_and_cycles_states` | Implemented |
| `events.py` | `StateChange`, `FaultEvent`, `SimulatedInspection`, `SimulatedUnit`, `SimulatedBatch` (with `inspected`, `failed`), `SimulatedOrder`, `SimulatedAlert`, `SimulationOutput` | Plain dataclasses consumed by `simulation_service.persist` | Covered through engine and API tests | Implemented |

Error handling across the package: `ValueError` for invalid configuration, translated to `ValidationError` by the service. Model details are in `docs/simulation/`.

### backend/app/investigation/

`__init__.py` carries the package docstring.

| File | Main symbols | Testing | Status |
|------|--------------|---------|--------|
| `rules.py` | `RuleThresholds` (with `cusum_baseline_hours` 3, `cusum_decision_interval` 0.10, derived `cusum_allowance` 0.025), `InvestigationContext` (with `cusum_onset_time`), `Evidence`, seven rule functions (`rule_defect_rate_elevation` to `rule_shared_material_lots` and `rule_cusum_onset`), `_cusum_rows`, `_hours_apart`, `_cusum_narrative`, `RULES` | `tests/unit/test_investigation_rules.py` (11 tests with a fake `QueryRunner`: `test_elevated_machine_produces_seven_evidence_cards_and_flags_batches`, `test_machine_in_line_with_fleet_is_not_elevated`, `test_fleet_wide_investigation_skips_machine_specific_rules`, `test_no_data_gives_a_plain_summary`, and seven CUSUM tests such as `test_cusum_signals_on_a_step_change_in_the_defect_rate`, `test_cusum_arithmetic_matches_a_hand_computed_example`, `test_cusum_narrative_never_uses_causal_language`) | Implemented |
| `engine.py` | `InvestigationReport`, `investigate(ctx, runner)` | Same unit tests; `tests/api/test_investigations_api.py` end to end | Implemented |
| `summary.py` | `build_summary(ctx)`, `_onset_agreement(threshold_onset, cusum_onset)` | `test_no_data_gives_a_plain_summary`, `test_cusum_narrative_compares_with_the_r3_onset`, and the evidence tests | Implemented |

Inputs: `InvestigationContext` and a `QueryRunner`. Outputs: `Evidence` cards and a summary string. Dependencies: `app.repositories.query_runner` (protocol only). Error handling: none inside the rules; database errors propagate from the runner. Rule semantics are documented in `docs/investigation/investigation-engine.md`; the decision to add R7 is ADR-0009.

### backend/app/repositories/

`__init__.py` is empty.

#### sql_loader.py

- Main symbols: `QUERIES_DIR` (`<repo>/database/queries`), `UnknownQueryError` (a `NotFoundError`), `_catalog()` (cached scan), `query_names()`, `load_sql(name)`, `load_query(name, expanding=())`.
- Inputs: `.sql` files. Outputs: raw SQL text or `TextClause`.
- Error handling: `UnknownQueryError` for unknown names, which the API maps to 404.
- Testing: `tests/unit/test_security_and_loader.py` (including `test_sql_catalog_contains_every_documented_query`).
- Status: Implemented.

#### query_runner.py

- Main symbols: `EXPANDING_PARAMS`, `QueryRunner` protocol (`run`, `sql`), `_jsonable`, `SqlQueryRunner(session)`.
- Inputs: query name and parameter mapping. Outputs: list of dictionaries with JSON-friendly values.
- Error handling: database errors propagate to the API error handlers.
- Testing: `tests/integration/test_queries.py::test_all_queries_run_and_agree`.
- Status: Implemented.

#### pagination.py

- Main symbols: `PageParams` (frozen; `limit` default 50, `offset` default 0), `PageResult[T]` (frozen; `items`, `total`), `paginate(session, stmt, paging) -> PageResult`.
- Behaviour: runs `SELECT COUNT(*)` over `stmt.order_by(None).subquery()` and then `stmt.limit(paging.limit).offset(paging.offset)`; the module docstring requires every paginated ordering to end in a unique column.
- Inputs: a SQLAlchemy `Select` and the parsed paging. Outputs: the page and the filtered total.
- Dependencies: SQLAlchemy only, so `app.api.deps` and `app.schemas.common` can import it without touching the query runner.
- Related: `catalog_service.list_machine_events`, `production_service.list_orders` and `list_batches`, `quality_service.list_inspections`, `investigation_service.list_investigations`, `analytics_service.recent_alerts`.
- Testing: `tests/api/test_pagination_api.py` (6 tests, including `test_pages_are_stable_disjoint_and_cover_every_order` and `test_offset_past_the_end_returns_empty_items_with_total`).
- Status: Implemented.

### backend/migrations/

| Path | Purpose | Status |
|------|---------|--------|
| `env.py` | Alembic environment: imports `app.models` to populate `Base.metadata`, injects `Settings.database_url`, supports offline (SQL to stdout) and online modes with `compare_type=True` | Implemented |
| `script.py.mako` | Template for new revisions | Implemented |
| `versions/20261104_0106_create_manufacturing_schema.py` | Revision `3a5e982c3679`: creates the 17 tables, CHECK and UNIQUE constraints, and indexes; `downgrade` drops tables in dependency order and explains why no `drop_index` calls are present | Implemented |
| `versions/20261107_2106_link_alerts_to_production_orders.py` | Revision `383273c26ef7` (revises `3a5e982c3679`): adds the nullable `alerts.production_order_id` column, the index `ix_alerts_production_order`, and the named foreign key `fk_alerts_production_order` to `production_orders.id` with `ON DELETE SET NULL`; `downgrade` drops the constraint first, then the index, then the column, because MySQL refuses to drop an index that backs a foreign key | Implemented |

Testing: `tests/conftest.py::migrated_database` runs `alembic upgrade head` on the test database once per session; `backend-ci.yml` applies migrations before the test run.

### backend/tests/

| Path | Scope | Needs MySQL | Status |
|------|-------|-------------|--------|
| `conftest.py` | Forces `APP_ENV=test`; session-scoped migration; per-test truncate, reference seed, and demo users; resets the login throttle around every test (`clean_login_throttle`, autouse); `client`, `engineer`, `operator`, `viewer`, `ids`, `simulated` fixtures; auto-marks `tests/api` and `tests/integration` as `integration` | Yes for the database fixtures | Implemented |
| `unit/test_quality_rules.py` | Measurement evaluation, classification, defect rate (4 tests) | No | Implemented |
| `unit/test_state_machines.py` | Order and machine transition tables (4) | No | Implemented |
| `unit/test_security_and_loader.py` | bcrypt, JWT round trip and tampering, SQL catalogue completeness (14 names) (3) | No | Implemented |
| `unit/test_simulation_engine.py` | Determinism, counts, tool wear, downtime, validation (10) | No | Implemented |
| `unit/test_investigation_rules.py` | Rules R1 to R7 with a fake runner, including the CUSUM arithmetic and narrative (11) | No | Implemented |
| `unit/test_alert_rules.py` | Days late, severity thresholds, message text, open order states (5) | No | Implemented |
| `unit/test_inspection_csv.py` | Header rules, field parsers, duplicates, row limit, blank and header-only files (14) | No | Implemented |
| `unit/test_login_throttle.py` | Sliding window, retry-after countdown, pruning, per-username and per-address limits, reset, limit validation, with a pinned clock (9) | No | Implemented |
| `api/test_analytics_api.py` | Query catalog, dashboard query execution, alert listing and acknowledgement (7) | Yes | Implemented |
| `api/test_alert_checks_api.py` | Overdue check: severity by days late, idempotence, re-raising after acknowledgement, orders due today, default clock, role guard, `production_order_id` in `AlertRead` (7) | Yes | Implemented |
| `api/test_auth_and_errors.py` | Health, login, token handling, role guards, error bodies, request ids (12) | Yes | Implemented |
| `api/test_inspection_import.py` | CSV import: valid file, header and field errors, reference and duplicate errors, limits, content types, role guard, rollback of a file with one bad row, the sample file against the demo scenario (16) | Yes | Implemented |
| `api/test_login_throttle_api.py` | 429 with `Retry-After` on the sixth attempt, lockout of a correct password, reset, per-address and per-username independence, unknown usernames (6) | Yes | Implemented |
| `api/test_machines_api.py` | Machine creation, duplicates, status change (3) | Yes | Implemented |
| `api/test_orders_api.py` | Order creation, validation, lifecycle, role checks (6) | Yes | Implemented |
| `api/test_pagination_api.py` | Defaults, disjoint and complete pages, offset past the end, invalid values, filters combined with paging (6) | Yes | Implemented |
| `api/test_batches_api.py` | Batch creation atomicity, rollback with an unavailable lot, quantity limits, lots, completion, quarantine and its idempotence, cancelled orders (9) | Yes | Implemented |
| `api/test_quality_api.py` | Inspection recording and validation, summary (3) | Yes | Implemented |
| `api/test_investigations_api.py` | Evidence generation on a simulated history (codes R1 to R7), lifecycle, evidence column order (4) | Yes | Implemented |
| `api/test_traceability_api.py` | Forward and backward traces, lot quarantine cascade (3) | Yes | Implemented |
| `api/test_simulation_api.py` | Persisted counts, determinism, validation (4) | Yes | Implemented |
| `integration/test_alert_order_link.py` | `SET NULL` on order delete keeps the alert, idempotence across sessions, the command commits and exits 0 (3) | Yes | Implemented |
| `integration/test_queries.py` | Every SQL file runs against simulated data and returns the documented shape (3) | Yes | Implemented |
| `integration/test_simulation_persistence.py` | A run spanning several 1000-row chunks persists exact counts; inspections point at the unit with the matching serial (2) | Yes | Implemented |
| `integration/test_transactions.py` | Rollback of partial writes, foreign keys, CHECK and ENUM constraints, batch lifecycle checks, batch deletion with units, atomic quantity increment, decimal precision (8) | Yes | Implemented |

The suite holds 162 test functions across 8 unit, 13 API, and 4 integration modules (counted from the files; parametrised cases add runs, and this document does not record a pass count). `backend-ci.yml` uploads `coverage.xml` as an artifact. A `.coverage` data file may appear under `backend/` after a local run; it is ignored by Git.

## database/

| Path | Purpose | Loader key | Parameters | Consumers | Status |
|------|---------|------------|------------|-----------|--------|
| `queries/01_machine_defect_rate_comparison.sql` | Defect rate per machine with fleet rate and rank (CTE, window functions) | `machine_defect_rate_comparison` | `window_start`, `window_end` | analytics, rule R1 | Implemented |
| `queries/02_production_performance.sql` | Order progress, duration, schedule status | `production_performance` | `limit` | analytics | Implemented |
| `queries/03_recurring_defects.sql` | Defect categories per machine with share and rank | `recurring_defects` | `window_start`, `window_end`, `machine_id` (nullable) | analytics, rule R2 | Implemented |
| `queries/04_material_lot_forward_trace.sql` | Batches that consumed a lot, with failures | `material_lot_forward_trace` | `lot_number` | traceability service (forward trace) | Implemented |
| `queries/05_unit_backward_trace.sql` | Lineage of a serial number with an inspection summary | `unit_backward_trace` | `serial_number` | traceability backward | Implemented |
| `queries/06_quality_after_machine_events.sql` | Defect rate before and after each event (LATERAL) | `quality_after_machine_events` | `machine_id`, `window_start`, `window_end`, `hours` | analytics | Implemented (header names the analytics endpoint as its only consumer; rule R4 uses `investigation.machine_events_before_onset`) |
| `queries/07_order_completion_summary.sql` | Planned versus completed with ROLLUP subtotals | `order_completion_summary` | none | analytics | Implemented |
| `queries/08_batches_requiring_review.sql` | Batches at or above a defect-rate threshold, not quarantined | `batches_requiring_review` | `window_start`, `window_end`, `threshold`, `machine_id` (nullable) | analytics, rule R5 | Implemented |
| `queries/09_daily_production_trend.sql` | Units and failed units per day and machine | `daily_production_trend` | `window_start`, `window_end` | analytics | Implemented |
| `queries/10_characteristic_control_chart.sql` | X-bar and S control chart by batch for one specification: three chained CTEs, `STDDEV_SAMP` and `VAR_SAMP` per subgroup, `SUM OVER ()` and `AVG OVER ()` for the grand mean, pooled standard deviation, and three-sigma `ucl` and `lcl`; the header states the formula and EXPLAIN notes | `characteristic_control_chart` | `specification_id` (required), `window_start`, `window_end`, `machine_id` (nullable) | analytics (control chart panel, SQL explorer) | Implemented |
| `queries/investigation/defect_onset.sql` | Hourly defect rate with `LAG` and cumulative rate (`bucket_start` formatted `%Y-%m-%dT%H:00:00`) | `investigation.defect_onset` | `machine_id`, `window_start`, `window_end` | rule R3 | Implemented |
| `queries/investigation/hourly_defect_rates.sql` | Hourly `inspected_count`, `failed_count`, and `defect_rate` for one machine, oldest first, no calendar scaffold; rule R7 appends `cusum` and `signal` in Python | `investigation.hourly_defect_rates` | `machine_id`, `window_start`, `window_end` | rule R7 | Implemented |
| `queries/investigation/machine_events_before_onset.sql` | Non-state-change events in a lookback window | `investigation.machine_events_before_onset` | `machine_id`, `onset_time`, `lookback_hours` | rule R4 | Implemented |
| `queries/investigation/shared_material_lots.sql` | Lots shared by a set of batches (expanding `IN`) | `investigation.shared_material_lots` | `batch_ids` (list) | rule R6 | Implemented |
| `schema/schema.sql` | Generated DDL snapshot from the migrated database (`export_schema.sh`), including `alerts.production_order_id`; not a source of truth | n/a | n/a | reviewers, `docs/database` | Implemented |
| `seeds/01_reference_data.sql` | Idempotent upserts for 3 products, 6 specifications, 3 machines (`CNC-01` to `CNC-03`), 5 defect types, 9 material lots | n/a | n/a | `app.seed`, test fixtures | Implemented |
| `seeds/demo_scenario.json` | Default simulation request: seed 42, 2026-11-02 06:00, 12 batches per machine, 20 units per batch, `TOOL_WEAR` on `CNC-03` from batch 4, `DOWNTIME` on `CNC-02` from batch 6 | n/a | n/a | `app.seed --demo` | Implemented |
| `seeds/sample_inspection_import.csv` | Sixteen rows for units `SIM0001-CNC-02-02-B04-U0001` to `U0008` of the demo scenario (`hole_position` and `thickness`), two of them without `inspected_at` and one with a `SURFACE_DAMAGE` code; the file `docs/quality/inspection-import.md` uses as its example | n/a | n/a | `POST /inspections/import`, `tests/api/test_inspection_import.py::test_sample_file_imports_against_the_demo_scenario` | Implemented |
| `documentation/README.md` | Guide to the database documentation set | n/a | n/a | readers | Implemented |

Query semantics and sample results are documented in `docs/database/queries.md`.

## scripts/

| Path | Purpose | Inputs | Error handling | Status |
|------|---------|--------|----------------|--------|
| `setup/init_databases.sh` | Creates the application and test databases and the least-privilege user with DML plus DDL on those two schemas; idempotent; used by `local_mysql.sh init`, docker-compose, and `backend-ci.yml` | `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, optional `MYSQL_ROOT_ARGS`, `MYSQL_CLIENT_ARGS` | `set -euo pipefail`; required variables checked up front; clears client environment variables that would redirect the connection | Implemented |
| `development/local_mysql.sh` | Private `mysqld` without Docker: `init`, `start`, `stop`, `status`, `shell`; data under `.local/mysql`; loopback only; strict SQL mode | `.env` | Refuses to run without `.env` or `mysqld`; refuses to start when the port is in use | Implemented |
| `development/reset_database.py` | Drops every table (foreign key checks off), then `alembic upgrade head` and `python -m app.seed [--demo]` as subprocesses | `--demo`, settings | `subprocess.run(check=True)` stops on failure | Implemented |
| `development/export_schema.sh` | `mysqldump --no-data` of the configured database into `database/schema/schema.sql` with a generated header | `.env` | `set -euo pipefail` | Implemented |
| `development/export_openapi.py` | Writes `app.openapi()` to `docs/api/openapi.json` (34 paths, 43 operations) and prints the path count | none | none | Implemented |
| `development/benchmark_simulation.py` | Times `simulation_service.run_simulation` for two request shapes (the demo shape, 3 machines by 12 batches by 20 units, and a large shape, 3 by 40 by 50), three repeats each, inside sessions that are rolled back; prints the median total time, the engine-only time, and rows per second (units plus inspections) (`make benchmark-sim`, which runs `uv run python ../scripts/development/benchmark_simulation.py` from `backend/`) | `.env`, a migrated and seeded database | Exits 2 when `APP_ENV` is `production` | Implemented (leaves no rows behind; InnoDB auto-increment counters still advance) |
| `development/render_diagrams.py` | Renders every `docs/media/diagrams/*.mmd` to an SVG next to it using Playwright and the Mermaid library from a CDN (`make render-diagrams`, which runs `uv run --group docs python ../scripts/development/render_diagrams.py` from `backend/`) | `.mmd` files | exits non-zero on a render failure | Implemented (requires the `docs` dependency group, an installed Google Chrome, and network access for the Mermaid CDN script) |
| `development/render_milestone_figures.py` | Renders each Mermaid block in `docs/milestones/*.md` to `docs/milestones/figures/<document>-<n>.png` (numbered by block order) with Playwright at device scale 4; reuses the browser launch and Mermaid page from `render_diagrams.py`, and `docs/milestones/build_documents.py` imports it (`make render-figures`, which runs `uv run --group docs python ../scripts/development/render_milestone_figures.py` from `backend/`) | `docs/milestones/*.md` | Prints each failed figure to stderr, continues, and exits 1 if any failed or no browser could be launched | Implemented (requires the `docs` dependency group and network access for the Mermaid CDN script) |
| `development/capture_screenshots.py` | Drives Chrome (the macOS Google Chrome install when present, otherwise Playwright's Chromium) through Playwright against the running frontend at `http://localhost:5173` (`FRONTEND_URL` overrides), signs in as the demo `engineer` account with `SEED_DEMO_PASSWORD` read from the repository `.env`, and writes `01-login.png` to `09-analytics-sql-explorer.png` into `docs/media/screenshots/` (`SCREENSHOT_DIR` overrides) at a 1600 by 1000 viewport. Needs the demo scenario loaded (`make reset-demo`), both servers running, and at least one investigation | `.env`, running servers | Exits 1 with a message when no investigation exists or `SEED_DEMO_PASSWORD` is missing; a screen that fails to load raises a Playwright error rather than writing a placeholder | Implemented (run on 2026-11-03; there is no Makefile target) |

## frontend/

The frontend is a React 19 and TypeScript single-page application built with Vite 7, styled with Tailwind CSS 4, charting with Recharts 3, data fetching with TanStack Query 5, and routing with React Router 7. It is described here at directory level. It has eleven routed screens (login plus ten application screens): Login, Overview, Machines, Orders, Batches, Inspections, Traceability, Investigations list, Investigation detail, Analytics, and Simulation. Browser tests written with Playwright Test live in `e2e/`.

| Path | Purpose | Status |
|------|---------|--------|
| `package.json`, `pnpm-lock.yaml` | pnpm package (`packageManager` pnpm 10.34.1) with scripts `dev`, `build`, `preview`, `lint`, `typecheck` (app, node, and e2e tsconfigs), `test`, `test:watch`, `test:e2e`, `test:e2e:report`, `format`, `format:check`; `@playwright/test` is a dev dependency | Implemented |
| `vite.config.ts` | React and Tailwind plugins, `@` alias to `src` and `@tests` alias to `tests`, manual chunks for the React libraries and Recharts, dev server on 5173 with `/api` proxied to `VITE_API_PROXY_TARGET` or `http://127.0.0.1:8000`, Vitest configuration (jsdom, `tests/setup.ts`, `src/**/*.test.{ts,tsx}`) | Implemented |
| `playwright.config.ts` | Playwright Test configuration: `testDir` `e2e`, Chromium project (installed Google Chrome when `E2E_BROWSER_CHANNEL=chrome`), base URL `E2E_BASE_URL` or `http://localhost:5183`, list and HTML reporters, trace on first retry, one retry and `forbidOnly` in CI; starts the backend with `uv run uvicorn app.main:app` on `E2E_API_PORT` (8013) from `../backend` and `pnpm dev` on the base URL's port with `VITE_API_PROXY_TARGET` pointed at the backend, reusing running servers outside CI; resolves `E2E_PASSWORD` from the environment or `SEED_DEMO_PASSWORD` in the repository `.env` before any server starts | Implemented |
| `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`, `tsconfig.e2e.json`, `eslint.config.js`, `.prettierrc`, `.prettierignore` | TypeScript (the e2e config extends the node config and covers `e2e/` and `playwright.config.ts`), ESLint 9, Prettier configuration | Implemented |
| `.gitignore` | `node_modules`, `dist`, `coverage`, `.vite`, `*.local`, `*.tsbuildinfo`; the Playwright output directories are ignored by the root `.gitignore` | Implemented |
| `index.html`, `src/main.tsx` | Entry point | Implemented |
| `e2e/` | Playwright specs: `login.spec.ts` (wrong password stays on the login page; the engineer lands on the overview with nine sidebar sections), `investigation.spec.ts` (an engineer opens, reviews, and closes an investigation on `CNC-03`), `traceability.spec.ts` (forward trace, backward trace, lot quarantine), `roles.spec.ts` (a viewer sees no mutating controls; a viewer token gets 403 on order creation), `analytics.spec.ts` (the SQL explorer runs `batches_requiring_review`); five files, nine tests. `support/env.ts` reads `E2E_PASSWORD` or `SEED_DEMO_PASSWORD`; `support/auth.ts` signs in through the form or the API and wraps authenticated `GET`s. `README.md` describes the run, the demo data assumptions, and the rows a run leaves behind | Implemented |
| `src/app/` | `router.tsx` (routes for login, overview, machines, orders, batches, quality, investigations and detail, traceability, analytics, simulation, with a catch-all redirect), `AppLayout.tsx`, `Sidebar.tsx`, `nav.ts` (nine sections), `providers.tsx`, `queryClient.ts` (TanStack Query client), `RequireAuth.tsx` | Implemented |
| `src/components/ui/` | Button, Chip, DataTable, Disclosure, Field, PageHeader, Pagination (`Pagination` with range text, previous and next buttons, and a page-size selector; `PageBody` dims the previous page while the next loads; with a test), Panel, SqlDisclosure (with a test), States, StatTile, StatusBadge | Implemented |
| `src/components/charts/` | ChartFrame (with a test), CountBarChart, DailyTrendChart, DefectRateChart, ControlChart (X-bar line chart with control and specification reference lines and out-of-control markers; with a test) | Implemented |
| `src/features/` | One folder per screen: `login`, `overview` (alerts list paged, order counts from envelope totals; with a test), `machines` (status form, `MachineEventsPanel` with the paged event timeline), `orders`, `batches`, `quality` (inspection form, paged table, `ImportInspectionsPanel.tsx` and `useImportInspections.ts` for the CSV upload with a row-error table; with a test), `investigations` (paged list, detail, evidence card, case summary, flagged batches, open form, status actions), `traceability` (search form, quarantine lot form), `analytics` (charts page, `ControlChartPanel.tsx` with specification and machine pickers running `characteristic_control_chart`, SQL explorer, window controls), `simulation` (fault scenario builder) | Implemented |
| `src/hooks/` | `AuthProvider.tsx` and `useAuth.ts` (auth context with `login`, `logout`, `can`), `queries.ts` (TanStack Query hooks and keys, `LOOKUP_PAGE` of 500 rows for lookups, `useOrderCounts` from single-row page totals, `keepPreviousData` on paged lists), `usePageState.ts` (`limit` and `offset` per screen with `resetOffset`), `invalidate.ts` (`invalidateProduction`, which refreshes the production-related query keys after a mutation), `useMediaQuery.ts` (CSS media query hook), and `AuthProvider.test.tsx` | Implemented |
| `src/services/` | `http.ts` (`API_PREFIX`, `ApiError` with `requestId`, `tokenStore` in `localStorage`, unauthorised event; a `FormData` body is sent as multipart without a `Content-Type` header), `api.ts` (`authApi`, `catalogApi` including `specifications` and paged `machineEvents`, `productionApi`, `qualityApi` including `importInspections`, `investigationApi`, `traceabilityApi`, `analyticsApi`, `simulationApi`) | Implemented |
| `src/types/` | `api.ts` (response and request types mirroring the backend schemas, including `Page<T>`, `PageParams`, `SpecificationListItem`, `InspectionImportResult`, `InspectionImportRowError`), `constants.ts` (status lists, default window, `PAGE_SIZES` 25, 50, 100, `DEFAULT_PAGE_SIZE` 50) | Implemented |
| `src/utils/` | `permissions.ts` (capabilities per role mirroring the backend route guards), `transitions.ts`, `format.ts`, `errors.ts` (`describeError`, `extractFieldErrors`, `extractImportRowErrors`, `isNotFound`), `chartTheme.ts`, `chartTransforms.ts` (including the control chart series, axis, and description helpers), `renderCell.tsx`, `statusTone.ts`, and the unit tests for `permissions`, `transitions`, `chartTransforms`, and `renderCell` | Implemented |
| `src/styles/index.css` | Tailwind entry stylesheet | Implemented |
| `tests/setup.ts`, `tests/helpers.tsx`, `tests/fixtures/controlChart.ts` | Vitest setup (jest-dom matchers, `ResizeObserver` stub, cleanup), render and fetch-mock helpers (`jsonResponse`, `pageOf`, `pageResponse`, `mockFetch`, `renderWithProviders`), and control chart fixture rows with the documented Query 10 limits | Implemented |
| `src/**/*.test.ts(x)` | Vitest files colocated with the code: `http`, `permissions`, `transitions`, `chartTransforms`, `renderCell`, `Pagination`, `SqlDisclosure`, `ChartFrame`, `ControlChart`, `ControlChartPanel`, `SqlExplorer`, `LoginPage`, `OrdersPage`, `OverviewPage`, `ImportInspectionsPanel`, `TraceabilityPage`, `EvidenceCard`, `AuthProvider` (18 files; this document does not record a pass count) | Implemented |
| `public/` | Static assets (`favicon.svg`) | Implemented |

Build artifacts such as `tsconfig.*.tsbuildinfo` may appear after `pnpm build`, and `playwright-report/` and `test-results/` after `pnpm test:e2e`; they are not part of the source.

## docs/

| Path | Owner and contents | Status |
|------|--------------------|--------|
| `docs/architecture/` | This document set: system overview, component design, data flow, repository structure | Implemented |
| `docs/decisions/` | ADR-0001 to ADR-0009 and an index | Implemented |
| `docs/media/diagrams/` | Mermaid sources: `system-architecture.mmd`, `backend-components.mmd`, `local-deployment.mmd` (architecture documentation), `er-diagram.mmd` (database documentation), and `manufacturing-workflow.mmd`, `investigation-workflow.mmd`, `traceability-relationships.mmd`, `simulation-event-flow.mmd`, plus one `<name>.svg` render per source produced by `make render-diagrams` | Implemented |
| `docs/media/screenshots/` | `README.md` plus nine PNG files (`01-login.png` to `09-analytics-sql-explorer.png`) captured on 2026-11-03 by `scripts/development/capture_screenshots.py` | Implemented |
| `docs/media/videos/` | Only a `README.md`; no video exists | Planned |
| `docs/api/openapi.json` | OpenAPI 3 document generated by `scripts/development/export_openapi.py`, 34 paths and 43 operations | Implemented |
| `docs/database/` | Database design, data dictionary, normalization, queries, seed data (owned separately) | Implemented by its owner |
| `docs/simulation/` | Simulation design and fault models (owned separately) | Implemented by its owner |
| `docs/investigation/` | Investigation engine and traceability design (owned separately) | Implemented by its owner |
| `docs/quality/` | `inspection-import.md`: the CSV import contract (request, file format, semantics, errors) (owned separately) | Implemented by its owner |
| `docs/requirements/` | Functional requirements, non-functional requirements, business rules (owned separately) | Implemented by its owner |
| `docs/ai_evidence/` | Responsible AI use record, annotated conversations, reflection notes | Implemented by its owner |
| `docs/milestones/` | Course milestone documents in Markdown with generated DOCX and PDF, plus `build_documents.py` and `html_pdf.py` (styled HTML rendered to PDF with Chrome through Playwright when the `docs` dependency group is installed) | Implemented by its owner |
| `docs/milestones/figures/` | PNG renders of the Mermaid blocks in the milestone Markdown files, written by `render_milestone_figures.py`; currently `week08-proposal-1.png` only | Implemented |
| `docs/development/`, `docs/testing/` | Setup guide and roadmap; testing strategy and test matrix. The `Makefile` header refers to `docs/development/setup-guide.md` | Implemented by its owner |

## .github/

| Path | Purpose | Status |
|------|---------|--------|
| `workflows/backend-ci.yml` | On push and pull request: MySQL 8.4 service, `uv sync --locked`, `.env` from the example, `init_databases.sh`, `alembic upgrade head`, Ruff check and format, mypy (blocking), pytest with coverage, coverage artifact | Implemented |
| `workflows/frontend-ci.yml` | On changes under `frontend/`: pnpm (version from `packageManager`) on Node 22, frozen install, lint, format check, typecheck, test, build; no-op without `package.json` | Implemented |
| `workflows/docs-lint.yml` | Fails on em dashes, en dashes, or emoji in Markdown; renders `.mmd` files with mermaid-cli (non-blocking) | Implemented |
| `workflows/compose-smoke.yml` | On changes to `docker-compose.yml`, `scripts/setup/`, `.env.example`, or itself, and on manual dispatch: builds a `.env` from the example, starts the `mysql` service and waits for its health check, verifies as root inside the container that both schemas and the least-privilege user with the expected grants exist, connects as the application user over TCP from the runner and checks that `mysql.user` is denied, then removes the volume | Implemented |
| `workflows/e2e.yml` | On push and pull request: MySQL 8.4 service, `uv sync --locked --group dev`, `.env` from the example with `APP_ENV=development` and both Vite ports in `CORS_ORIGINS`, `init_databases.sh`, `alembic upgrade head`, `app.seed --demo`, pnpm frozen install, `playwright install --with-deps chromium`, `pnpm test:e2e` with `CI=1` and `E2E_PASSWORD`; uploads `playwright-report` on failure | Implemented |
| `ISSUE_TEMPLATE/` | Bug report, feature request, database change proposal; blank issues disabled | Implemented |
| `pull_request_template.md` | Summary, type, linked issue, testing, AI assistance disclosure | Implemented |

## Known discrepancies between files and intended design

These were found while writing this document set and are reported here. Items that were fixed after the first version of this document have been removed.

1. `docker-compose.yml` mounts `./scripts/setup/init_databases.sh` as `/docker-entrypoint-initdb.d/01_init.sh` and passes `MYSQL_ROOT_ARGS` and `MYSQL_CLIENT_ARGS`. The Docker path has not been executed on the development machine because Docker is not installed; the `compose-smoke.yml` workflow is the only place it runs.
2. `InvestigationCreate.product_id` (`backend/app/schemas/investigation.py`) is validated in `investigation_service.open_investigation` and stored on the investigation, but it is not passed to `InvestigationContext` and no rule in `backend/app/investigation/` filters by product.
3. `GET /analytics/queries` lists all fourteen SQL files, but `GET /analytics/queries/{name}` runs only the eight in `DASHBOARD_QUERIES`. For the other six, `run_dashboard_query` in `backend/app/services/analytics_service.py` raises a 422 `ValidationError` with the runnable names in `details.runnable_queries`; only a name that matches no SQL file returns 404. The catalogue marks the six with `runnable: false`.
4. `request_id_middleware` returns the request id in `X-Request-ID` on every response and `app/api/errors.py` puts it at the top level of every error body, but the middleware writes no log line. The id therefore appears in application logs only where a handler or service passes it in `extra`, so a successful request cannot be looked up in the logs by its id.
5. `simulation_service.py` logs a `request_id` of the form `seed-<seed>` (the simulation seed) instead of the id assigned by the middleware, so that log field has two meanings.
6. `.env.example` sets `MYSQL_PORT=3306` while the documented local setup (and this checkout's `.env`) uses 3307; the difference is intentional for machines with a system MySQL on 3306 but is not explained in the example file.
7. `frontend/e2e/README.md` and `frontend/e2e/investigation.spec.ts` describe an investigation on `CNC-03` as producing evidence cards `R1` to `R6`; the engine now also produces `R7`. The spec asserts only the first six cards in order and does not assert the total, so it still passes.
8. The login throttle in `backend/app/core/throttle.py` keeps its counts in the memory of one API process. Running uvicorn with several workers, or several hosts, gives each process its own counts, so the configured limit is per process rather than per deployment; the module docstring states this.
