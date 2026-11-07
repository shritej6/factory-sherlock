# System overview

Factory Sherlock is a manufacturing simulation, quality control, and defect investigation platform built on MySQL 8. It was developed as a university database systems final project and is structured the way a small production service would be: a FastAPI backend organised as a modular monolith, a MySQL schema managed by Alembic, SQL analysis queries kept as files that the application executes verbatim, and a React frontend that is being built alongside the backend.

The product is inspired by concepts found in manufacturing execution systems such as Rockwell Automation FactoryTalk (production orders, batches, machine events, traceability, quality investigations). It is an independent project and is not affiliated with any vendor.

This document describes the system at the level of layers, module boundaries, dependency rules, and cross-cutting concerns. Component internals are in [component-design.md](component-design.md), request and transaction flows are in [data-flow.md](data-flow.md), and a file-by-file inventory is in [repository-structure.md](repository-structure.md). Schema design, the simulation model, and the investigation rules are documented by their owners under `docs/database/`, `docs/simulation/`, and `docs/investigation/`.

## Purpose

The platform answers three kinds of question about a (simulated) machining cell:

1. What was produced, on which machine, from which material lots, and with what inspection results. This is the manufacturing execution and traceability part: production orders, production batches, production units, material lots, inspections, and defect types.
2. What is the current quality picture. Dashboard queries compute defect rates per machine, recurring defect types, daily production trends, order completion, and batches that need review.
3. Why quality deteriorated. An engineer opens an investigation over a time window and optionally a machine; a rule engine runs seven SQL-backed rules (R1 to R7) and stores each finding as an evidence card together with the exact SQL and result rows that produced it.

Because the project has no physical factory, a deterministic simulation engine generates production history with injectable faults (tool wear, calibration drift, increased variation, material issues, downtime) so that the investigation engine has realistic data to work on.

## Implementation status

| Area | Status | Notes |
|------|--------|-------|
| Backend API (34 paths, 43 operations under `/api/v1`) | Implemented | `backend/app`, exported to `docs/api/openapi.json` |
| MySQL schema (17 tables) and Alembic migrations | Implemented | Two revisions in `backend/migrations/versions/`: `3a5e982c3679` creates the 17 tables, `383273c26ef7` adds `alerts.production_order_id` |
| SQL query library (14 files) loaded at runtime | Implemented | `database/queries/`: ten numbered files plus four under `investigation/` |
| Paginated list endpoints | Implemented | `backend/app/repositories/pagination.py`, `app/schemas/common.py` (`Page[T]`), `app/api/deps.py` (`Paging`); six list endpoints return `{items, total, limit, offset}` |
| CSV inspection import | Implemented | `POST /inspections/import`; `backend/app/services/inspection_csv.py`, `inspection_import.py`; sample file `database/seeds/sample_inspection_import.csv`; documented in `docs/quality/inspection-import.md` |
| Overdue order alerts | Implemented | `backend/app/services/alert_service.py`; `POST /analytics/alerts/checks/overdue-orders`; command `python -m app.jobs.check_overdue_orders` (`make check-overdue`) |
| Simulation engine | Implemented | `backend/app/simulation`; bulk-insert persistence in `app/services/simulation_service.py`; timing script `scripts/development/benchmark_simulation.py` (`make benchmark-sim`) |
| Investigation engine (rules R1 to R7) | Implemented | `backend/app/investigation`; R7 (CUSUM onset) is recorded in ADR-0009 |
| JWT authentication, four roles, login throttle | Implemented | `backend/app/core/security.py`, `backend/app/core/throttle.py`, `backend/app/api/deps.py` |
| Seed command and demo scenario | Implemented | `backend/app/seed.py`, `database/seeds/` |
| Local MySQL scripts and docker-compose | Implemented (local script executed on the development machine; compose file executed only by the `compose-smoke.yml` workflow) | `scripts/`, `docker-compose.yml`; Docker is not installed on the development machine |
| Frontend (React 19, TypeScript, Vite 7, Tailwind 4, React Router 7, TanStack Query 5, Recharts 3) | Implemented | `frontend/src/features/*`: Login, Overview, Machines (with a paged event timeline), Orders, Batches, Inspections (with the CSV import panel), Traceability, Investigations list, Investigation detail (case board with evidence cards and show-the-SQL), Analytics (charts, per-characteristic control chart, SQL explorer), Simulation; paged tables share `components/ui/Pagination.tsx` and `hooks/usePageState.ts` |
| Backend automated tests | Implemented | `backend/tests`: 8 unit modules, 13 API modules, 4 integration modules (162 test functions counted from the files; this document does not record a pass count); API and integration tests run against the `_test` database |
| Frontend automated tests | Implemented | Vitest and Testing Library (`frontend/tests/setup.ts`, `helpers.tsx`, `fixtures/controlChart.ts`); 18 colocated test files |
| End-to-end browser tests | Implemented | Playwright Test in `frontend/e2e/` (five spec files, nine tests) with `frontend/playwright.config.ts`, which starts the backend on port 8013 and the Vite server on port 5183; `pnpm test:e2e` |
| Continuous integration | Implemented | Five workflows: `.github/workflows/backend-ci.yml`, `frontend-ci.yml`, `docs-lint.yml`, `compose-smoke.yml`, `e2e.yml` |

## Layers

The backend is a single deployable process. Inside it, code is arranged in layers that only depend downward (see "Dependency direction rules").

### Presentation

The React single-page application in `frontend/`. It talks to the backend over HTTP with JSON bodies and a `Bearer` JWT in the `Authorization` header; the one exception is the CSV import, which `src/services/http.ts` sends as a `multipart/form-data` body (a `FormData` with a single `file` part, no `Content-Type` header of its own). The token is kept in `localStorage` by `http.ts`. During development the Vite dev server on port 5173 proxies `/api` to `http://127.0.0.1:8000` (`vite.config.ts`; `VITE_API_PROXY_TARGET` overrides the target for the end-to-end run); the backend's CORS configuration (`CORS_ORIGINS`, default `http://localhost:5173`) allows direct calls as well. Directory structure: `src/app` (layout, router, auth guard, providers), `components` (`ui` including `Pagination.tsx`, `charts` including `ControlChart.tsx`), `features` (one folder per screen), `hooks` (`useAuth`, `usePageState`, TanStack Query hooks), `services` (`http.ts`, `api.ts`), `types`, `utils` (formatting, permissions mirroring the backend role guards, transitions, chart helpers, error extraction), `styles`. Paged lists read the backend's `Page` envelope and request `limit=500` when a list is used as a lookup. `frontend/e2e/` holds the Playwright browser tests, which run the real frontend against the real backend and MySQL. Frontend details are described at directory level only in this document set.

### API

`backend/app/api`. FastAPI route modules grouped by resource (health, auth, catalog, production, quality, investigations, traceability, analytics, simulation) and mounted under `/api/v1` by `router.py`. Routes validate input through Pydantic v2 schemas in `backend/app/schemas`, obtain a database session, the current user, and the `limit`/`offset` paging parameters through dependencies in `deps.py`, call one service function, and convert ORM objects to response schemas. `POST /inspections/import` is the one route without a request schema: it receives a multipart `UploadFile`, reads at most `MAX_FILE_BYTES + 1` bytes, and hands the bytes, content type, and file name to the import service. `request_id.py` gives every request a short id and echoes it in the `X-Request-ID` header. `errors.py` maps typed application errors and SQLAlchemy errors to HTTP responses that never expose SQL text or stack traces.

### Application services

`backend/app/services`. One module per bounded area: `auth_service`, `catalog_service`, `production_service`, `quality_service`, `traceability_service`, `investigation_service`, `analytics_service`, `simulation_service`, `alert_service` (the overdue order check), and the pair `inspection_csv` (CSV parsing, no database access) and `inspection_import` (resolution and persistence of a CSV upload through `quality_service.record_inspection`). Services own orchestration: they load rows, apply domain rules, write ORM objects, run raw SQL through the repository layer, and raise typed errors. They receive a `Session` as an argument and never commit; the request-scoped session commits on success, and the command in `app/jobs` commits the session it opened itself.

### Jobs

`backend/app/jobs`. Commands meant to run on a schedule rather than per request. `check_overdue_orders.py` (`uv run python -m app.jobs.check_overdue_orders [--as-of ISO-8601]`, wrapped by `make check-overdue`) opens a `SessionLocal` session, calls `alert_service.raise_overdue_order_alerts`, commits, logs one JSON line with the counts and the new alert ids, and exits 0; any exception rolls the session back and propagates. The same service function backs `POST /analytics/alerts/checks/overdue-orders`, so the scheduled path and the API path cannot drift.

### Domain

`backend/app/domain`. Pure business rules with no database or HTTP dependencies. `quality_rules.py` defines how a measurement is evaluated against a specification, how a failure is classified into a defect type code, and the single definition of `defect_rate`. `state_machines.py` holds the transition tables for machines, production orders, production batches, and investigations plus `assert_transition`. Both the API services and the simulation engine use these functions, so the synthetic factory obeys the same rules as manual operations.

### Data access

Two mechanisms, deliberately kept separate:

- ORM: SQLAlchemy 2 declarative models in `backend/app/models`, one module per aggregate (product, machine, material, production, quality, investigation, user) plus shared enums and a timestamp mixin. Services use these for all writes and for simple reads.
- Raw SQL: `backend/app/repositories/sql_loader.py` reads every `.sql` file under `database/queries/` into an in-memory catalog keyed by file stem (numeric prefix removed, subdirectory as a dotted prefix, for example `investigation.defect_onset`). `query_runner.py` executes a named query with bound parameters and returns JSON-friendly rows. Analytics, traceability, and the investigation rules go through this path so the SQL the documentation describes is the SQL that runs.
- Pagination: `backend/app/repositories/pagination.py` defines the frozen `PageParams` (`limit`, `offset`) and `PageResult[T]` (`items`, `total`) dataclasses and `paginate(session, stmt, paging)`, which runs a `SELECT COUNT(*)` over the filtered statement with its ordering removed and then the windowed select. The six list services that read growing tables return a `PageResult`; the routes wrap it in the `Page[T]` schema.

### Simulation subsystem

`backend/app/simulation`. A pure engine (`SimulationEngine`) that takes a frozen `SimulationConfig` and a `Catalog` of reference rows and returns a `SimulationOutput` of plain dataclasses: orders, batches, units, inspections, machine state changes, fault events, alerts, and final machine states. All randomness flows through one `random.Random(seed)`, so the same inputs produce the same output. The engine never imports SQLAlchemy; `simulation_service.persist` maps the output onto ORM rows inside one transaction.

### Investigation subsystem

`backend/app/investigation`. `engine.investigate` runs the seven rules in `rules.py` in order against a `QueryRunner` and a mutable `InvestigationContext` that later rules read from earlier rules (for example R4 uses the onset time found by R3, R6 uses the batch ids found by R5, and R7 compares its CUSUM signal hour with the R3 onset in its narrative). Each rule returns an `Evidence` card holding the rule code, a title, a narrative, the query name, the query SQL, and the result rows, or `None` when it has nothing to say. R7 (`rule_cusum_onset`) runs `investigation.hourly_defect_rates` and appends two derived columns, `cusum` and `signal`, to the rows in Python before storing them; it is skipped without a machine or with fewer than `cusum_baseline_hours` (3) hourly rows. `summary.py` turns the context into a short written summary and, when both onset estimates exist, states whether they fall in the same hour. Rules only read; `investigation_service` persists the report.

### MySQL

MySQL 8 is the system of record. The schema is 17 tables created by the first Alembic migration (`3a5e982c3679`); the second migration (`383273c26ef7`) adds the nullable `alerts.production_order_id` column with its index and a `SET NULL` foreign key, so the overdue check can find the open alert for an order without parsing message text. The tables include three many-to-many junction tables: `batch_materials` (production batches to material lots), `inspection_defects` (inspections to defect types), and `investigation_batches` (investigations to production batches). Status columns are MySQL `ENUM`s mirroring `backend/app/models/enums.py`, and CHECK constraints guard quantities and windows. The application connects as a least-privilege user created by `scripts/setup/init_databases.sh`. Schema details are documented under `docs/database/`.

## High-level system architecture

The same diagram is kept as Mermaid source in [`docs/media/diagrams/system-architecture.mmd`](../media/diagrams/system-architecture.mmd).

```mermaid
flowchart TB
    subgraph Presentation["Presentation (frontend/)"]
        SPA["React + TypeScript SPA<br/>Vite dev server :5173"]
        E2E["Playwright e2e tests<br/>(frontend/e2e)"]
    end

    subgraph Backend["Backend process (FastAPI, uvicorn)"]
        subgraph API["API layer (app/api)"]
            Routes["Route modules<br/>health, auth, catalog, production, quality,<br/>investigations, traceability, analytics, simulation"]
            Deps["deps.py<br/>DbSession, CurrentUser, role guards, Paging"]
            Errors["errors.py<br/>typed error to HTTP mapping"]
        end
        subgraph Services["Application services (app/services)"]
            Svc["auth, catalog, production, quality,<br/>traceability, investigation, analytics, simulation,<br/>alert, inspection_import + inspection_csv"]
        end
        subgraph Domain["Domain (app/domain)"]
            Rules["quality_rules.py<br/>state_machines.py"]
        end
        subgraph Sim["Simulation subsystem (app/simulation)"]
            Engine["SimulationEngine<br/>config, faults, measurement, machine_state, events"]
        end
        subgraph Inv["Investigation subsystem (app/investigation)"]
            InvEngine["investigate()<br/>rules R1 to R7, summary"]
        end
        subgraph Data["Data access"]
            ORM["SQLAlchemy models<br/>(app/models)"]
            Runner["sql_loader.py + query_runner.py<br/>+ pagination.py (app/repositories)"]
        end
        subgraph Core["Cross-cutting (app/core)"]
            Cfg["config, database, security, throttle,<br/>clock, logging, exceptions"]
        end
    end

    Jobs["app/jobs/check_overdue_orders.py<br/>(CLI, own session)"]
    Files["database/queries/*.sql<br/>(14 files)"]
    DB[("MySQL 8<br/>17 tables, Alembic managed")]

    SPA -->|"HTTP JSON or multipart + Bearer JWT"| Routes
    E2E -.->|"drives the browser"| SPA
    Routes --> Deps
    Routes --> Svc
    Jobs --> Svc
    Svc --> Rules
    Svc --> Engine
    Svc --> InvEngine
    Engine --> Rules
    Svc --> ORM
    Svc --> Runner
    InvEngine --> Runner
    Runner -->|"reads at startup"| Files
    ORM --> DB
    Runner --> DB
    Core -.-> API
    Core -.-> Services
    Core -.-> Data
```

## Module boundaries

| Package | May import from | Must not import from |
|---------|-----------------|----------------------|
| `app.api` | `app.services`, `app.schemas`, `app.models` (enums and `User` for typing), `app.repositories.pagination` (the `PageParams` dataclass only), `app.core` | `app.simulation`, `app.investigation`, `app.repositories.query_runner`, `app.repositories.sql_loader` |
| `app.jobs` | `app.services`, `app.core` | `app.api`, ORM models directly |
| `app.services` | `app.domain`, `app.models`, `app.schemas`, `app.repositories`, `app.simulation`, `app.investigation`, `app.core` | `app.api`, `app.jobs` |
| `app.domain` | `app.models.enums`, `app.core.exceptions` | `app.services`, `app.api`, SQLAlchemy sessions, HTTP |
| `app.simulation` | `app.domain`, `app.models.enums` | SQLAlchemy sessions, `app.services`, `app.api` |
| `app.investigation` | `app.repositories.query_runner` (the `QueryRunner` protocol) | ORM models, `app.services`, `app.api` |
| `app.repositories` | `app.core`, SQLAlchemy | `app.services`, `app.api`, domain |
| `app.models` | `app.core.database` (`Base`) | everything above it |
| `app.schemas` | `app.models.enums`, `app.repositories.pagination` (`PageParams` and `PageResult` for `Page.from_result`) | services, ORM sessions |
| `app.core` | third-party libraries and other `app.core` modules | any other `app` package |

The one place where this table bends is `app.domain.state_machines`, which imports `InvalidTransitionError` from `app.core.exceptions`; `core` is treated as a leaf shared by every layer. `app.repositories.pagination` is likewise treated as a leaf: it holds two dataclasses and one function with no model imports, so `deps.py` and `schemas/common.py` import it without reaching the query runner.

## Dependency direction rules

1. Dependencies point downward: API to services to domain and data access. Nothing below the service layer knows about FastAPI, HTTP status codes, or request objects.
2. Services raise typed errors from `app.core.exceptions`; only `app.api.errors` translates them into HTTP responses.
3. The simulation engine and the investigation rules are pure with respect to persistence. The engine receives a `Catalog` loaded by the service and returns dataclasses; the rules receive a `QueryRunner` protocol that tests can fake.
4. Raw SQL lives in `database/queries/`, never inline in Python. Services and rules refer to queries by name; the loader resolves the file.
5. Enumerations are defined once in `app.models.enums` and reused by ORM columns (as MySQL `ENUM`), Pydantic schemas, state machines, and the simulation.
6. Configuration is read only through `app.core.config.get_settings()`; no module reads `os.environ` directly.
7. Commands in `app.jobs` call the same service functions as the routes and own their own session and commit; nothing is implemented twice for the scheduled path.

## Cross-cutting concerns

### Configuration

`app/core/config.py` defines a `pydantic-settings` `Settings` class populated from environment variables and from the repository root `.env` (a `.env` in the current directory overrides it). It exposes computed fields: `effective_database` appends `_test` when `APP_ENV=test` so the test suite can never touch development data; `database_url` builds the `mysql+pymysql` URL; `cors_origin_list` splits `CORS_ORIGINS`. `login_max_failures` (default 5) and `login_window_seconds` (default 900) size the login throttle. Secrets (`mysql_password`, `jwt_secret_key`, `seed_demo_password`) are declared with `repr=False` so they do not appear in logs or reprs. `get_settings()` is cached with `lru_cache`. Alembic's `env.py` reads the same settings, so migrations and the application always target the same database.

### Sessions and transactions

`app/core/database.py` builds one engine per process (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`) and a `sessionmaker` with `autoflush=False` and `expire_on_commit=False`. `get_db_session` yields a request-scoped session: it commits when the route handler returns normally, rolls back when anything raises, and always closes. `deps.py` declares `DbSession` with `scope="function"` so the session closes, and therefore commits, before the response is sent; a failed commit becomes an error response rather than a 200 followed by a rollback. Services call `session.flush()` to surface constraint errors early and to obtain generated ids, but never `commit()`. The consequence is that every endpoint is one transaction: production batch creation (order status change, batch, junction rows, units), the CSV inspection import (every row of the file or none), simulation persistence (orders, batches, units, inspections, events, alerts, machine status), investigation creation (investigation, evidence cards, batch links), and the overdue order check (every new alert of one run) each either fully succeed or leave nothing behind. The scheduled command in `app/jobs` opens its own `SessionLocal` session and commits it after the service call.

### Logging

`app/core/logging.py` installs a single JSON formatter on the root logger and on uvicorn's loggers. Each line carries timestamp, level, logger, message, and, when present on the record, `request_id`, `user_id`, and `operation`. `app/api/request_id.py` assigns a 12 character id to every request and returns it in the `X-Request-ID` header, but writes no log line itself; the id reaches the log only through the error handlers (every `AppError` is logged at INFO as `request rejected` with `request_id`, `operation`, `error`, and `status`; database and unexpected errors are logged with the traceback). The throttle logs `login throttled` with the `Retry-After` value, and the import logs the row and failure counts. Handlers and services log identifiers only, never request bodies, passwords, tokens, or text from an uploaded file.

### Errors

`app/core/exceptions.py` defines `AppError` (status 400) and subclasses `NotFoundError` (404), `ConflictError` (409), `ValidationError` (422), `InvalidTransitionError` (422, raised by state machines), `AuthenticationError` (401), `AuthorizationError` (403), and `RateLimitedError` (429, raised by the login throttle; carries `retry_after_seconds`). Each carries a message and an optional `details` dictionary. `app/api/errors.py` registers handlers that return `{"error", "message", "details", "request_id"}` for `AppError` (adding a `Retry-After` header for `RateLimitedError`), FastAPI `RequestValidationError` (422 with per-field messages), SQLAlchemy `IntegrityError` (MySQL 1062 duplicate key becomes 409, 1452 foreign key violation becomes 422, anything else 500), `OperationalError` (1205 lock wait timeout and 1213 deadlock become 409 with a retry message, anything else 503), and any other exception (500). Database-level messages are logged with the request id and never returned to clients. `catalog_service._flush_or_conflict` additionally converts duplicate-key failures during flush into a `ConflictError` with a specific message, and the CSV import collects every row problem into `details.errors` as `{row, field, message}` before raising one 422.

### Authentication and authorisation

Passwords are hashed with bcrypt (`app/core/security.py`). `POST /api/v1/auth/login` returns an HS256 JWT containing `sub` (user id), `role`, `iat`, and `exp` (`JWT_ACCESS_TOKEN_MINUTES`, default 120). `auth_service.authenticate` compares against a fixed placeholder hash when the username does not exist, so an unknown user costs the same time as a wrong password and the error message is the same for both. Failed logins are throttled by `app/core/throttle.py`: `LoginThrottle` counts failures per lower-cased username and per client address in memory, and once a key reaches `LOGIN_MAX_FAILURES` (default 5) inside a sliding window of `LOGIN_WINDOW_SECONDS` (default 900) the next attempt for that key is rejected with 429 and a `Retry-After` header before any password work. A successful login clears the username's failures but not the address's. The route reads the direct peer address and ignores `X-Forwarded-For`; the store is one dictionary per API process, so several workers would each keep their own counts. `get_current_user` in `app/api/deps.py` decodes the bearer token and then loads the user row; the role in the token is informational and the database row decides whether the account is active and which role applies. Four roles exist: `ADMIN`, `ENGINEER`, `OPERATOR`, `VIEWER`. Reads require any authenticated user; writes use the `Operator` (admin, engineer, operator) and `Engineer` (admin, engineer) dependencies. ADMIN is included in every write set; no route is admin-only. Alert acknowledgement, the CSV inspection import, and the overdue order check require `Operator`, so a VIEWER receives 403. The health endpoint is unauthenticated. At the database level the application user has DML plus the DDL needed to run migrations on the two project schemas only (see ADR-0007).

## Related documents

- [component-design.md](component-design.md): backend components, request flow, local deployment.
- [data-flow.md](data-flow.md): sequence diagrams for batch creation, the CSV inspection import, simulation persistence, investigation evidence generation, and the overdue order check.
- [repository-structure.md](repository-structure.md): directory tree and file inventory.
- [../decisions/README.md](../decisions/README.md): architecture decision records.
- `docs/database/`, `docs/simulation/`, `docs/investigation/`, `docs/quality/`: schema, simulation model, rule, and import documentation (owned separately).
- `docs/api/openapi.json`: generated OpenAPI document (`scripts/development/export_openapi.py`).
