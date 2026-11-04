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
| NFR-1.6 | Clients never receive SQL text from errors, stack traces, or driver messages. | `api/errors.py` maps `IntegrityError` to a generic 409, `OperationalError` to 503, and any other exception to 500, each with a `request_id` for log correlation. | API test forcing an integrity error and checking the body. |
| NFR-1.7 | Secrets are never committed or logged. | `.env` is git-ignored; `.env.example` holds placeholders; `Settings` marks `mysql_password`, `jwt_secret_key`, `seed_demo_password` with `repr=False`; the JSON log formatter emits only `request_id`, `user_id`, `operation`. | Repository scan for secrets; log inspection. |
| NFR-1.8 | The application connects to MySQL as a least-privilege user. | `scripts/setup/init_databases.sh` grants DML plus the DDL needed for migrations on the two project schemas only; root is used only by setup scripts. | Inspection of grants (`SHOW GRANTS`). |
| NFR-1.9 | Browser access is limited to configured origins. | `CORSMiddleware` with `CORS_ORIGINS` (default `http://localhost:5173`), explicit methods and headers. | Manual check from the frontend dev server. |
| NFR-1.10 | Input is validated at the boundary. | Pydantic schemas with `extra="forbid"`, patterns for codes, numeric ranges, decimal places; business validation in services returns typed 422 errors. | API tests for each rejected input class. |

Known gaps: no rate limiting on login; no refresh tokens or revocation (tokens stay valid until expiry even if the user is deactivated, although `get_current_user` reloads the row so deactivated users are rejected on the next request); `JWT_SECRET_KEY` strength is not validated; the health endpoint is unauthenticated by design.

## NFR-2 Reliability and data integrity

| ID | Requirement | Current implementation | Verification |
|----|-------------|------------------------|--------------|
| NFR-2.1 | Every request is one transaction: multi-table writes either fully succeed or leave nothing behind. | `core/database.py::get_db_session` commits on normal return and rolls back on any exception; services flush but never commit. | Integration tests for batch creation failure, simulation persistence failure, and lot quarantine cascade. |
| NFR-2.2 | Database constraints back every business rule that can be expressed declaratively. | UNIQUE on codes, numbers, serials, (unit, specification), (product, characteristic), (investigation, sequence); CHECK on quantities, tolerance, window order; FOREIGN KEY with explicit RESTRICT, CASCADE, SET NULL; ENUM status columns. | Integration tests that bypass the service and expect `IntegrityError`. |
| NFR-2.3 | Stale pooled connections do not cause request failures after idle periods. | `create_engine(..., pool_pre_ping=True, pool_size=5, max_overflow=10)`. | Observed behaviour after MySQL `wait_timeout`; no automated test. |
| NFR-2.4 | A database outage returns a clear 503 rather than a 500. | `OperationalError` handler. | API test with the engine pointed at a closed port. |
| NFR-2.5 | Seeding is idempotent. | `INSERT ... ON DUPLICATE KEY UPDATE` in `01_reference_data.sql`; `ensure_demo_users` updates existing accounts. | Run the seed twice and compare row counts. |
| NFR-2.6 | Historical inspection results stay stable when a specification changes. | `inspections.result` is stored, not recomputed. | Unit test of `record_inspection` followed by a tolerance change. |

Known gaps: no retry with backoff for transient database errors; no connection health endpoint beyond `GET /health`; no backups or point-in-time recovery are configured in this repository.

## NFR-3 Determinism and reproducibility

| ID | Requirement | Current implementation | Verification |
|----|-------------|------------------------|--------------|
| NFR-3.1 | The simulation produces identical output for identical inputs. | Single `random.Random(seed)`; frozen config and catalog; fixed iteration order. See `docs/simulation/simulation-design.md`. | Unit test comparing two engine runs; integration test comparing persisted measured values after two seeds of an empty database. |
| NFR-3.2 | Investigation results are reproducible for the same database state. | Rules are pure functions over query results; no randomness; fixed rule order. | Integration test opening two investigations on the same window and comparing evidence rows. |
| NFR-3.3 | The schema can be rebuilt from scratch on any machine. | Single Alembic migration; `scripts/development/reset_database.py` drops and rebuilds; `database/schema/schema.sql` is a generated snapshot for reading. | Running `reset_database.py --demo` on a fresh database. |
| NFR-3.4 | The SQL the documentation describes is the SQL that runs. | `sql_loader.py` reads `database/queries/*.sql` verbatim; the API returns the text with each result; evidence cards store it. | Comparison of `GET /analytics/queries/{name}.sql` with the file. |
| NFR-3.5 | Dependencies are pinned. | `backend/uv.lock`, `frontend/pnpm-lock.yaml`. | `uv sync --frozen`, `pnpm install --frozen-lockfile`. |

## NFR-4 Performance

No benchmark has been run on this repository, and this document does not claim response times or throughput figures. The expectations below describe design intent and the mechanisms that support it; measurements belong in the test matrix once they are taken.

| ID | Expectation | Supporting design |
|----|-------------|-------------------|
| NFR-4.1 | Dashboard queries over the demo data set (three machines, 35 batches, 700 units, 1400 inspections) return interactively. | Indexes `ix_inspections_time_result`, `ix_production_batches_machine_time`, `ix_production_batches_order`, `ix_machine_events_machine_time`, `ix_production_orders_status`; CTEs and window functions avoid repeated scans; query headers document the intended index use. |
| NFR-4.2 | A default simulation run (12 batches of 20 units on three machines) completes within a single HTTP request without streaming. | The engine is in-memory; persistence uses ORM inserts with per-batch flushes. Larger requests (up to 200 batches of 500 units per machine) are permitted by the schema limits but have not been timed. |
| NFR-4.3 | Investigation creation runs six queries and stores their rows; it is expected to be dominated by query time. | Rows are stored as JSON; no pagination of evidence rows is implemented. |
| NFR-4.4 | List endpoints are bounded. | `limit` parameters with maxima (inspections 1000, events 500, alerts 200, analytics rows 500). Order and batch lists have no limit and return every row. |

Known gaps: `GET /production-orders` and `GET /production-batches` are unpaginated; the simulation inserts units one object at a time rather than with bulk inserts.

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

The frontend is implemented and these requirements apply to it. No accessibility audit, keyboard walkthrough, or contrast measurement has been run, so none of them is verified.

| ID | Requirement |
|----|-------------|
| NFR-6.1 | All interactive controls are reachable and operable with a keyboard, with a visible focus indicator. |
| NFR-6.2 | Charts rendered with Recharts are accompanied by a table or text alternative of the same data (the SQL explorer rows satisfy this for analytics). |
| NFR-6.3 | Colour is not the only carrier of status (machine state, PASS/FAIL, batch status) and text contrast meets WCAG 2.1 AA. |
| NFR-6.4 | Form fields have associated labels and validation errors are announced in text. |
| NFR-6.5 | The application is usable at 320 px width without horizontal scrolling of primary content. |

Verification is planned through ESLint accessibility rules, Testing Library queries by role and label in Vitest, and a manual keyboard pass before the final demonstration.

## NFR-7 Reproducibility of the development environment

| ID | Requirement | Current implementation |
|----|-------------|------------------------|
| NFR-7.1 | A developer on macOS or Linux can run the full stack with documented commands. | `docs/development/setup-guide.md`; `scripts/development/local_mysql.sh` (no Docker) or `docker-compose.yml`. |
| NFR-7.2 | The test suite never touches development data. | `APP_ENV=test` switches `effective_database` to `<MYSQL_DATABASE>_test`, which `init_databases.sh` creates with the same grants. |
| NFR-7.3 | Tooling is version-locked. | Python `>= 3.12` in `pyproject.toml`, `uv.lock`; Node packages in `pnpm-lock.yaml`; MySQL 8.4 image in `docker-compose.yml`. |
| NFR-7.4 | Generated artefacts are regenerable, not hand-edited. | `docs/api/openapi.json` (export script), `database/schema/schema.sql` (`export_schema.sh`), Alembic migration as the schema source of truth. |

## NFR-8 Observability

| ID | Requirement | Current implementation |
|----|-------------|------------------------|
| NFR-8.1 | Logs are structured. | Single-line JSON from `core/logging.py` with timestamp, level, logger, message, and optional `request_id`, `user_id`, `operation`; uvicorn loggers are routed through the same formatter. |
| NFR-8.2 | Server-side failures are correlatable. | Error handlers generate a 12-character `request_id`, log the exception with it, and return it in the response `details`. |

Known gaps: successful requests have no request id; there is no metrics endpoint or tracing.
