# Testing strategy

This document defines how Factory Sherlock is tested: the shape of the test pyramid for this repository, the test categories, how the test database is isolated, and where each of the twelve required scenarios from the project brief lives. The backend tests under `backend/tests/` and the frontend tests under `frontend/src/**/*.test.ts(x)` exist; this document describes the strategy and where each scenario is tested. The last full local `uv run pytest` run (2026-11-03) reported 100 passed with 95 percent coverage of `app`, and `pnpm test` ran 13 files and 39 tests, all passing. Per-scenario results and the gaps are recorded in [test-matrix.md](test-matrix.md).

Tooling: `pytest` with `pytest-cov` and `httpx` (FastAPI `TestClient`) for the backend (`backend/pyproject.toml`, dev dependency group); Vitest with Testing Library and jsdom for the frontend (`frontend/vite.config.ts`, `frontend/tests/setup.ts`). The pytest marker `integration` is declared for tests that need a running MySQL test database; `backend/tests/conftest.py` adds it automatically to everything under `tests/api` and `tests/integration`.

Current layout: 5 unit modules, 9 API modules, and 2 integration modules (81 test functions; 100 test cases with parametrisation), plus 13 frontend test files. Browser-driven end-to-end tests are planned and not yet written.

## Test pyramid for this repository

The code base has a thick domain and simulation layer that is deliberately free of I/O, a thin API layer, and a set of behaviours that only exist in MySQL (constraints, window functions, LATERAL joins, ROLLUP). The pyramid follows that shape.

| Level | Share of tests (target) | What it covers | Needs MySQL |
|-------|-------------------------|----------------|-------------|
| Unit | about 70 percent | `domain/quality_rules.py`, `domain/state_machines.py`, `simulation/*` (engine, faults, measurement, state tracker, config validation), `investigation/rules.py` and `summary.py` with a fake `QueryRunner`, `core/security.py`, `repositories/sql_loader.py` catalogue naming, Pydantic schema validation. | No |
| Integration (API and database) | about 20 percent | Route handlers through `TestClient` against the test database: authentication and roles, order and batch workflows, inspections, quarantine cascade, investigation creation, simulation persistence, constraint violations, error response shapes; the SQL files executed against seeded data. | Yes |
| End-to-end | about 10 percent (target; none written yet) | The demo scenario from seed to investigation to quarantine through the API, and browser flows against the frontend. | Yes |

Unit tests run without any environment; the engine in `core/database.py` is created at import time but does not connect until a session is used, so importing `app` modules in unit tests is safe as long as `.env` or environment variables provide a parsable configuration.

## Test categories

### Unit tests (`backend/tests/unit/`)

- Quality rules: boundary of `abs(measured - target) <= tolerance` (exactly on the limit passes), classification by characteristic and sign, `defect_rate` rounding and the zero-inspection case.
- State machines: every allowed edge in `MACHINE_TRANSITIONS`, `ORDER_TRANSITIONS`, `BATCH_TRANSITIONS`, `INVESTIGATION_TRANSITIONS` succeeds; a sample of forbidden edges raises `InvalidTransitionError` with `details.allowed` populated; terminal states reject everything.
- Simulation: `SimulationConfig` and `Catalog` invariants; `combined_effect` arithmetic for each fault kind and for combinations; `MeasurementGenerator` quantisation and sign of gross deviations; `SimulationEngine` determinism (same seed equals, different seed differs), batch and unit counts, order grouping, lot rotation, DOWNTIME slot loss and state sequence, alert emission at the threshold with the consecutive-run rule, final machine states.
- Investigation: each rule against a fake runner returning canned rows, including the `None` paths (R2 with no defects, R3 and R4 without a machine, R4 without onset, R6 without batches); context propagation between rules; `build_summary` wording for elevated and non-elevated cases and the absence of causal phrasing.
- Security: hash and verify round trip, malformed hash returns false, token encode and decode, expired token raises `AuthenticationError`.
- Schemas: `extra="forbid"`, patterns, ranges, decimal places.
- SQL loader: file stem to name mapping (`01_...` prefix removed, subdirectory dotted), unknown name raises `UnknownQueryError`.

### API tests (`backend/tests/api/`)

Run with `TestClient(app)` against the test database. A session-scoped fixture runs `alembic upgrade head` on the test database (and refuses to run unless the effective database name ends with `_test`); a per-test fixture truncates every table, applies the reference seed, and creates the demo users. Login fixtures obtain tokens for the engineer, operator, and viewer accounts.

- Authentication and authorisation: 401 without or with an invalid token, 403 for roles outside the allowed set, 200 for allowed roles (alert acknowledgement is checked for VIEWER 403 and OPERATOR success).
- Error contract: error bodies have `error`, `message`, and `details`; 422 bodies carry `details.errors[]` with `field` and `message`; 409 (database constraint) and 500 bodies carry `details.request_id`. The current tests check the 401, 403, 404, 409, and 422 cases; the 500 and 503 bodies are not tested.
- Resource endpoints: create, read, list, update, status change for products, machines, material lots, orders, batches, inspections, investigations, alerts; traceability forward and backward; simulation runs.

### Database integration tests (`backend/tests/integration/`, marker `integration`)

- Constraints: UNIQUE, CHECK, FOREIGN KEY, and ENUM rejections observed as `IntegrityError` when writing through the ORM without the service checks.
- Transactions: a failure in the middle of `create_batch`, `quarantine_lot`, or `persist` leaves no partial rows.
- SQL files: `test_all_queries_run_and_agree` executes each of the twelve queries against the simulated data and asserts the key columns and cross-query agreement (for example the failed count equals the simulation result and `order_completion_summary` has an `ALL`/`ALL` row); the SQL catalogue completeness check is in `tests/unit/test_security_and_loader.py`.

### Simulation tests

Unit tests on the engine as listed above, plus `tests/api/test_simulation_api.py::test_simulation_is_deterministic_across_runs`, which posts the same request twice and compares the failed inspection counts. A per-serial comparison of `measured_value` and `result` is not implemented.

### Business rule tests

Each rule in `docs/requirements/business-rules.md` with a service or state machine enforcement layer gets at least one test that triggers the rejection and one that passes at the boundary (for example batch quantity exactly equal to the remaining quantity).

### Investigation tests

Unit tests with a fake runner (`tests/unit/test_investigation_rules.py`), plus API tests (`tests/api/test_investigations_api.py`) that run the small simulated scenario, open an investigation for CNC-03, and assert structural properties: six cards R1 to R6 in order, the summary mentions an elevated rate, the oversize diameter and `TOOL_WEAR`, the first card carries the SQL of query 01 and a CNC-03 row, the R4 card lists the `TOOL_WEAR` event, a healthy machine is not flagged, and stored evidence rows keep the SQL column order. Assertions that every linked batch id appears in R5 rows and that each card's `query_sql` equals the file content are not implemented.

### End-to-end tests

No end-to-end test has been written. The intended flow is: seed, run the demo simulation, read alerts, open the investigation, quarantine the worst batch, confirm it disappears from `batches_requiring_review`, close the investigation with a conclusion, verify `CLOSED` is terminal. Pieces of it are covered separately by API tests. Vitest component tests render the screens against mocked fetches (login, orders role gating, traceability, evidence card, SQL explorer, SQL disclosure) together with unit tests for the HTTP client, permissions, transitions, chart transforms, and cell rendering.

## Test database isolation

`backend/app/core/config.py` computes `effective_database`: when `APP_ENV=test` the application, Alembic, and the reset script all use `<MYSQL_DATABASE>_test` (`factory_sherlock_test` with the default name). `scripts/setup/init_databases.sh` creates both schemas with identical grants for the application user, so the test suite can run migrations itself.

Running the backend tests:

```bash
cd backend
APP_ENV=test uv run alembic upgrade head     # once, or let the fixture do it
APP_ENV=test uv run pytest                   # unit + API + integration
APP_ENV=test uv run pytest -m "not integration"
APP_ENV=test uv run pytest --cov=app --cov-report=term-missing
```

Rules:

- Tests must never run with `APP_ENV=development`; `conftest.py` sets `APP_ENV=test` before importing the application, and the migration fixture asserts that the effective database name ends with `_test`.
- The test schema is reset by `uv run python ../scripts/development/reset_database.py` with `APP_ENV=test` when a clean slate is needed.
- Unit tests do not open sessions; API and integration tests truncate every table before each test, so they must not run concurrently against the same test database.
- The seed command's demo accounts need `SEED_DEMO_PASSWORD`; the test fixture creates users directly with `hash_password` so no secret is read from the environment (`TEST_PASSWORD` in `tests/conftest.py`).

Frontend tests run with `pnpm test` (Vitest, jsdom, `src/**/*.test.{ts,tsx}`) and do not need the backend. `pnpm lint`, `pnpm typecheck`, and `pnpm build` also pass.

## The twelve required scenarios

| # | Scenario | Category | Test location | What is asserted (design; see test-matrix.md for what the tests actually assert) |
|---|----------|----------|------------------|------------------|
| 1 | Valid order creation | API | `tests/api/test_orders_api.py` | Engineer `POST /production-orders` returns 201, status PLANNED, `quantity_completed` 0; the row exists. |
| 2 | Invalid order rejection | API | `tests/api/test_orders_api.py`, `tests/api/test_auth_and_errors.py` | Bad order number pattern, zero quantity, unknown field: 422 with field errors; unknown product: 404; duplicate order number: 409; viewer: 403. |
| 3 | Machine state transitions | Unit, API | `tests/unit/test_state_machines.py`, `tests/api/test_machines_api.py` | Allowed edges succeed and record a STATE_CHANGE event; FAULT to RUNNING returns 422 listing allowed targets; severity CRITICAL on FAULT. |
| 4 | Deterministic simulation | Unit, API | `tests/unit/test_simulation_engine.py`, `tests/api/test_simulation_api.py` | Equal outputs for equal seed and catalog; different seeds differ; persisted measured values identical across two runs on a clean database. |
| 5 | Quality measurement validation | Unit, API | `tests/unit/test_quality_rules.py`, `tests/api/test_quality_api.py` | Boundary pass; spec from another product: 422; unknown unit: 404; defect codes on PASS: 422; duplicate inspection: 409. |
| 6 | Defect classification | Unit | `tests/unit/test_quality_rules.py` | Oversize and undersize by sign for diameter characteristics; hole position; dimensional default; computed code always attached to a failed inspection. |
| 7 | High defect-rate detection | Unit, integration | `tests/unit/test_simulation_engine.py`, `tests/unit/test_investigation_rules.py`, `tests/integration/test_queries.py` | Engine raises HIGH_DEFECT_RATE at the first batch at or above 0.15 and not again in a consecutive run; R1 sets `elevated` by the threshold formula; `batches_requiring_review` returns batches at or above the threshold and excludes quarantined ones. |
| 8 | Material lot traceability | API, integration | `tests/api/test_traceability_api.py`, `tests/integration/test_queries.py` | Forward trace of a seeded lot lists every batch linked in `batch_materials` with unit counts; backward trace of a serial returns its batch, machine, order, product, and lots; unknown lot or serial: 404. |
| 9 | Batch quarantine | API | `tests/api/test_batches_api.py`, `tests/api/test_traceability_api.py` | Batch quarantine sets status and reason and creates an alert; second quarantine: 422; lot quarantine quarantines all linked non-quarantined batches and returns them; quarantined lot rejected by `POST /production-batches`. |
| 10 | Transaction rollback | API, integration | `tests/api/test_batches_api.py`, `tests/integration/test_transactions.py` | `create_batch` with one unavailable lot among several leaves no batch, units, or order status change; forcing an `IntegrityError` during `quarantine_lot` leaves the lot AVAILABLE and all batches unchanged. |
| 11 | Foreign key validation | Integration | `tests/integration/test_transactions.py` | Inspection with a non-existent specification is rejected; deleting a product referenced by an order fails (RESTRICT); deleting a batch cascades to units and material links; deleting a machine referenced by an alert sets `machine_id` NULL. |
| 12 | API error handling | API | `tests/api/test_auth_and_errors.py` and the error assertions in the other API modules | 401, 403, 404, 409, 422, 503 bodies follow `{"error", "message", "details"}`; 500 bodies contain a `request_id` and no SQL or stack text; validation errors list field paths. |

## Coverage and quality gates

- Target line coverage for `backend/app` of 80 percent with the domain, simulation, and investigation packages at or near 100 percent, since they are pure and cheap to cover. The last full run measured 95 percent for `app` overall; per-package figures were not recorded.
- `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy app` pass before any test run is considered green.
- Flaky tests are fixed or deleted, not skipped. Tests that depend on random simulation outcomes must assert properties that hold for every seed (counts, ordering, structure) or pin a seed and compute the expectation from the formulas.
- Continuous integration is defined in `.github/workflows/`: `backend-ci.yml` (MySQL 8.4 service, Ruff check and format, blocking mypy, migrations, pytest with coverage), `frontend-ci.yml` (lint, typecheck, test, build), and `docs-lint.yml` (forbidden characters). These workflows have not been observed running on GitHub from this checkout; the commands above are run locally.
