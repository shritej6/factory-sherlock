# Non-functional requirements

Each requirement states what the system is expected to provide, how the current code meets or does not meet it, and how it is verified. Where no measurement has been taken, the document says so rather than quoting a number.

## NFR-1 Security

| ID | Requirement | Current implementation | Verification |
|----|-------------|------------------------|--------------|
| NFR-1.1 | Passwords are stored only as salted hashes. | bcrypt via `core/security.py::hash_password`; `verify_password` returns false on a malformed hash instead of raising. | Unit test of hash and verify; inspection of the `users.password_hash` column after seeding. |
| NFR-1.2 | API access requires a signed, expiring token. | HS256 JWT with `sub`, `role`, `iat`, `exp` (`JWT_ACCESS_TOKEN_MINUTES`, default 120); `create_access_token` refuses to run without `JWT_SECRET_KEY`; expired and invalid tokens return 401. | API tests for missing, invalid, and expired tokens. |
| NFR-1.3 | Authorization is enforced per endpoint by role, and the database row, not the token, decides the role and active flag. | `get_current_user` reloads the user; `require_roles` returns 403 with required roles. | API tests per role for each mutating endpoint. |
| NFR-1.4 | Login does not reveal whether a username exists. | Same `AuthenticationError("Invalid username or password")` for unknown user, wrong password, and inactive account. | API test comparing responses. |
| NFR-1.5 | SQL injection is not possible through API parameters. | All ORM access is parameterised; raw SQL files use named bind parameters executed through `text()`; query names are looked up in a fixed dictionary (`DASHBOARD_QUERIES`) before execution. | Code review; API test that a crafted query name returns 404. |
| NFR-1.6 | Clients never receive SQL text from errors, stack traces, or driver messages. | `api/errors.py` maps `IntegrityError` (1062 to 409, 1452 to 422, else 500), `OperationalError` (1205 and 1213 to 409; 3819 to 422 with only the constraint name in `details`; connection errors 2002, 2003, 2006, 2013 and pool timeouts to 503 "The database is not reachable"; anything else to 503 "The database is unavailable"), `DataError` (1406 to 422, else 500), and any other exception to 500, each with a `request_id` for log correlation and a fixed message. | `tests/unit/test_error_mapping.py` on the pure `classify_*` functions; `tests/api/test_error_contract.py` forces each class through the real app and checks the body has only the documented keys. |
| NFR-1.7 | Secrets are never committed or logged. | `.env` is git-ignored; `.env.example` holds placeholders; `Settings` marks `mysql_password`, `jwt_secret_key`, `seed_demo_password` with `repr=False`; the JSON log formatter emits only the allowlisted record fields `request_id`, `user_id`, `operation`, `error`, `status`, `retry_after_seconds` (`core/logging.py::LOGGED_FIELDS`). | Repository scan for secrets; log inspection. |
| NFR-1.8 | The application connects to MySQL as a least-privilege user. | `scripts/setup/init_databases.sh` grants DML plus the DDL needed for migrations on the two project schemas only; root is used only by setup scripts. | Inspection of grants (`SHOW GRANTS`). |
| NFR-1.9 | Browser access is limited to configured origins. | `CORSMiddleware` with `CORS_ORIGINS` (default `http://localhost:5173`), explicit methods and headers. | Manual check from the frontend dev server. |
| NFR-1.10 | Input is validated at the boundary. | Pydantic schemas with `extra="forbid"`, patterns for codes, numeric ranges, decimal places; business validation in services returns typed 422 errors; the CSV import (`services/inspection_csv.py`, `services/inspection_import.py`) validates the whole file before any row is written and reports every problem with its row and column; `api/body_limit.py` rejects a request body over 64 KiB (1 MiB + 64 KiB for the import) with 413 before authentication and before the body is parsed. | API tests for each rejected input class, including `tests/api/test_inspection_import.py` and `tests/api/test_body_limit_api.py`. |
| NFR-1.11 | Repeated failed logins are slowed down without letting one shared address lock other users out. | `core/throttle.py::LoginThrottle`, called from `auth_service.authenticate` after the user lookup and before the bcrypt check. The account bucket (the user id when the username matches a row, otherwise the NFKD, mark-stripped, casefolded username, so spelling variants share one bucket) is checked before verification: after `LOGIN_MAX_FAILURES` (default 5) failures or reserved slots within `LOGIN_WINDOW_SECONDS` (default 900) the endpoint returns 429 `RateLimitedError` with `details.retry_after_seconds` and a `Retry-After` header. The client address is counted only after a failed verification; when it already holds the maximum, that failed attempt is answered 429 instead of 401, so a correct password is never rejected because of the address alone. `check` reserves a slot that `record_failure` or `record_success` resolves, so concurrent requests cannot exceed the limit. A successful login clears the account's failures but not the address's. The address is `request.client.host` (`None` skips it); uvicorn is started with `--no-proxy-headers`, so it is the TCP peer and `X-Forwarded-For` is never applied. | Unit tests with a pinned clock (`tests/unit/test_login_throttle.py`, 16 test functions including a 20-thread concurrency test); API tests through `POST /auth/login` (`tests/api/test_login_throttle_api.py`, 10 tests, two client addresses). |

Known gaps: the login throttle counts per API process, so several workers would each allow `LOGIN_MAX_FAILURES` attempts; no rate limit on authenticated endpoints; no refresh tokens or revocation (tokens stay valid until expiry even if the user is deactivated, although `get_current_user` reloads the row so deactivated users are rejected on the next request); `JWT_SECRET_KEY` strength is not validated; the health endpoint is unauthenticated by design.

## NFR-2 Reliability and data integrity

| ID | Requirement | Current implementation | Verification |
|----|-------------|------------------------|--------------|
| NFR-2.1 | Every request is one transaction: multi-table writes either fully succeed or leave nothing behind. | `core/database.py::get_db_session` commits on normal return and rolls back on any exception; services flush but never commit. | Integration tests for batch creation failure, simulation persistence failure, and lot quarantine cascade; API test that one invalid CSV row leaves no inspection behind (`test_one_invalid_row_rolls_back_the_whole_file`). |
| NFR-2.2 | Database constraints back every business rule that can be expressed declaratively. | UNIQUE on codes, numbers, serials, (unit, specification), (product, characteristic), (investigation, sequence); CHECK on quantities, tolerance, window order; FOREIGN KEY with explicit RESTRICT, CASCADE, SET NULL; ENUM status columns. | Integration tests that bypass the service and expect `IntegrityError`. |
| NFR-2.3 | Stale pooled connections do not cause request failures after idle periods. | `create_engine(..., pool_pre_ping=True, pool_size=5, max_overflow=10)`. | Observed behaviour after MySQL `wait_timeout`; no automated test. |
| NFR-2.4 | A database outage returns a clear 503 rather than a 500. | `OperationalError` and pool `TimeoutError` handlers: connection errors and pool timeouts answer "The database is not reachable", other operational errors "The database is unavailable". | API test with the engine pointed at a closed port (`test_database_unavailable_returns_503_for_health_and_protected_routes`) plus the monkeypatched 1040 and pool-timeout cases in `tests/api/test_error_contract.py`. |
| NFR-2.5 | Seeding is idempotent. | `INSERT ... ON DUPLICATE KEY UPDATE` in `01_reference_data.sql`; `ensure_demo_users` updates existing accounts. | Run the seed twice and compare row counts. |
| NFR-2.6 | Historical inspection results stay stable when a specification changes. | `inspections.result` is stored, not recomputed. | Unit test of `record_inspection` followed by a tolerance change. |

Known gaps: no retry with backoff for transient database errors; no connection health endpoint beyond `GET /health`; no backups or point-in-time recovery are configured in this repository.

## NFR-3 Determinism and reproducibility

| ID | Requirement | Current implementation | Verification |
|----|-------------|------------------------|--------------|
| NFR-3.1 | The simulation produces identical output for identical inputs. | Single `random.Random(seed)`; frozen config and catalog; fixed iteration order. See `docs/simulation/simulation-design.md`. | Unit test comparing two engine runs; integration test comparing persisted measured values after two seeds of an empty database. |
| NFR-3.2 | Investigation results are reproducible for the same database state. | Rules are pure functions over query results; no randomness; fixed rule order. | Integration test opening two investigations on the same window and comparing evidence rows. |
| NFR-3.3 | The schema can be rebuilt from scratch on any machine. | Three Alembic migrations (`3a5e982c3679` creates the 17 tables; `383273c26ef7` adds `alerts.production_order_id` with its index and foreign key; `6c1f0d2a9b47` adds the five list-ordering and control-chart indexes), each with a `downgrade()`; `scripts/development/reset_database.py` drops and rebuilds; `database/schema/schema.sql` is a generated snapshot for reading. | Running `reset_database.py --demo` on a fresh database. |
| NFR-3.4 | The SQL the documentation describes is the SQL that runs. | `sql_loader.py` reads `database/queries/*.sql` verbatim; the API returns the text with each result; evidence cards store it. | Comparison of `GET /analytics/queries/{name}.sql` with the file. |
| NFR-3.5 | Dependencies are pinned. | `backend/uv.lock`, `frontend/pnpm-lock.yaml`. | `uv sync --frozen`, `pnpm install --frozen-lockfile`. |

## NFR-4 Performance

Two benchmarks have been run on this repository, both timing a service call without HTTP on the development machine (local MySQL 8.4). The simulation persistence benchmark (`make benchmark-sim`, `scripts/development/benchmark_simulation.py`) is recorded in `docs/simulation/simulation-design.md` under "Persistence path". The inspection import benchmark (`scripts/development/benchmark_inspection_import.py`; 5000 rows, 250 failing with an explicit defect code, median of three runs) is recorded in `docs/quality/inspection-import.md`: one `record_inspection` call per row cost 10507 SQL statements and 1.47 s (3396 rows per second); the bulk path in `inspection_import._write_inspections` costs 15 statements and 0.11 s (46051 rows per second). No response-time or throughput figures for API endpoints over HTTP are claimed. The expectations below describe design intent and the mechanisms that support it; further measurements belong in the test matrix once they are taken.

| ID | Expectation | Supporting design |
|----|-------------|-------------------|
| NFR-4.1 | Dashboard queries over the demo data set (three machines, 35 batches, 700 units, 1400 inspections) return interactively. | Indexes `ix_inspections_time_result`, `ix_inspections_time_id`, `ix_inspections_spec_time` (both predicates of the control chart query; it replaced the implicit `specification_id` index on `inspections`), `ix_production_batches_machine_time`, `ix_production_batches_order`, `ix_production_batches_started_id`, `ix_production_orders_status`, `ix_production_orders_created_id`, `ix_investigations_created_id`, `ix_machine_events_machine_time`, `ix_alerts_created`, `ix_alerts_production_order`; the four `(time, id)` indexes match the paginated orderings; CTEs and window functions avoid repeated scans; query headers document the intended index use; EXPLAIN plans at demo and grown volume are in `docs/database/queries.md` and `docs/database/database-design.md` section 6. |
| NFR-4.2 | A default simulation run (12 batches of 20 units on three machines) completes within a single HTTP request without streaming. | The engine is in-memory; persistence writes orders, batches, and alerts through the ORM and units, inspections, inspection defects, and machine events with chunked multi-row INSERTs of at most 1000 rows (`simulation_service._bulk_insert`). The demo shape and a 3 x 40 x 50 shape (6000 units, 12000 inspections) are timed by `make benchmark-sim`; the largest shape the schema permits (200 batches of 500 units per machine) has not been timed. |
| NFR-4.3 | Investigation creation runs seven queries (one per rule R1 to R7) and stores their rows; it is expected to be dominated by query time. | Rows are stored as JSON; no pagination of evidence rows is implemented. |
| NFR-4.4 | List endpoints and request bodies are bounded. | Six list endpoints (orders, batches, inspections, machine events, alerts, investigations) take `limit` (1 to 500, default 50) and `offset` (0 to 1,000,000) and return `{items, total, limit, offset}` (`repositories/pagination.py`, `schemas/common.py::Page`); batches and investigations filter by repeatable `status` in SQL, and `GET /production-orders/status-counts` replaces one list request per status with one GROUP BY; analytics query rows are capped by `limit` (1 to 500); the CSV import accepts at most 1 MiB and 5000 rows, and `api/body_limit.py` caps every request body (64 KiB, 1 MiB + 64 KiB for the import) with 413. `tests/api/test_pagination_api.py` checks defaults, stable disjoint pages, the offset bound, and rejected values; `tests/api/test_status_filters_api.py` checks the filters and the constant statement count of the batch list. |

Known gaps: the reference lists (`GET /products`, `GET /machines`, `GET /material-lots`, `GET /defect-types`, `GET /specifications`) return every row, which is acceptable for reference data of a few rows but is not bounded; each paginated response runs a second `COUNT(*)` statement for `total`; the filtered batch list (`machine_id` plus the `(started_at, id)` ordering) has no `(machine_id, started_at, id)` index and relies on `ix_production_batches_machine_time`; no response-time figures for API endpoints over HTTP have been measured.

## NFR-5 Maintainability

| ID | Requirement | Current implementation |
|----|-------------|------------------------|
| NFR-5.1 | Layers depend downward only; HTTP concerns stay in the API layer. | Services raise typed `AppError` subclasses; only `api/errors.py` knows status codes. Module boundaries are tabulated in `docs/architecture/system-overview.md`. |
| NFR-5.2 | Business rules are defined once. | `domain/quality_rules.py` and `domain/state_machines.py` are used by the API services and the simulator; `defect_rate` has a single definition. |
| NFR-5.3 | Static checks pass. | `ruff` (E, F, I, B, UP, N, SIM, RUF; line length 100) and `mypy --strict` with the pydantic plugin on `app`; ESLint, Prettier, and `tsc` for the frontend. See `docs/development/coding-standards.md`. |
| NFR-5.4 | Configuration has one entry point. | `core/config.py::get_settings`; no module reads `os.environ`. |
| NFR-5.5 | SQL is reviewable as files with a documentation header. | Every file under `database/queries` starts with business question, tables, techniques, parameters, result, and (for dashboard queries) performance notes. |
| NFR-5.6 | The API contract is exported and versioned. | `scripts/development/export_openapi.py` writes `docs/api/openapi.json`; routes are mounted under `/api/v1`. |

## NFR-6 Accessibility

The frontend is implemented and these requirements apply to it. A code-level accessibility pass on 2026-11-07 computed contrast ratios from the colour tokens in `frontend/src/styles/index.css` and `chartTheme.ts` (every text pair at or above 4.5:1 after the `ink-faint` shade change; chart series at or above 3:1), moved focus into the mobile navigation drawer when it opens (the drawer was removed on 2026-11-08 with the sidebar, see ADR-0011) and back to the toggle when a disclosure closes, gave repeated row actions accessible names that include the batch number, and added Vitest tests for these behaviours (`AppLayout`, `Disclosure`, `BatchActions`, `States`, `StatTile`). No screen-reader session and no manual walkthrough at 320 px width has been recorded, so NFR-6.5 and the screen-reader part of NFR-6.1 remain unverified.

| ID | Requirement |
|----|-------------|
| NFR-6.1 | All interactive controls are reachable and operable with a keyboard, with a visible focus indicator. |
| NFR-6.2 | Charts rendered with Recharts are accompanied by a table or text alternative of the same data (the SQL explorer rows satisfy this for analytics). |
| NFR-6.3 | Colour is not the only carrier of status (machine state, PASS/FAIL, batch status) and text contrast meets WCAG 2.1 AA. |
| NFR-6.4 | Form fields have associated labels and validation errors are announced in text. |
| NFR-6.5 | The application is usable at 320 px width without horizontal scrolling of primary content. |

Verification so far: Testing Library queries by role and label in Vitest and the contrast computation above. Still planned: ESLint accessibility rules and a manual keyboard and screen-reader pass before the final demonstration.

## NFR-7 Reproducibility of the development environment

| ID | Requirement | Current implementation |
|----|-------------|------------------------|
| NFR-7.1 | A developer on macOS or Linux can run the full stack with documented commands. | `docs/development/setup-guide.md`; `scripts/development/local_mysql.sh` (no Docker) or `docker-compose.yml`. |
| NFR-7.2 | The test suite never touches development data. | `APP_ENV=test` switches `effective_database` to `<MYSQL_DATABASE>_test`, which `init_databases.sh` creates with the same grants. |
| NFR-7.3 | Tooling is version-locked. | Python `>= 3.12` in `pyproject.toml`, `uv.lock`; Node packages in `pnpm-lock.yaml`; MySQL 8.4 image in `docker-compose.yml`. |
| NFR-7.4 | Generated artefacts are regenerable, not hand-edited. | `docs/api/openapi.json` (export script), `database/schema/schema.sql` (`export_schema.sh`), Alembic migrations as the schema source of truth. |

## NFR-8 Observability

| ID | Requirement | Current implementation |
|----|-------------|------------------------|
| NFR-8.1 | Logs are structured. | Single-line JSON from `core/logging.py` with timestamp, level, logger, message, and the optional allowlisted fields `request_id`, `user_id`, `operation`, `error`, `status`, `retry_after_seconds`; uvicorn loggers are routed through the same formatter (`tests/unit/test_logging_formatter.py`). |
| NFR-8.2 | Server-side failures are correlatable. | `request_id_middleware` assigns a 12-character `request_id` to every request and returns it in the `X-Request-ID` header; the error handlers log the exception with it and put it at the top level of the error body (`{error, message, details, request_id}`); the 413 from the body cap carries the same id. |

Known gaps: successful requests have no request id; there is no metrics endpoint or tracing.
