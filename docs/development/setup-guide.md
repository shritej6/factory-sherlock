# Setup guide

Verified against the scripts and configuration in this repository: `.env.example`, `docker-compose.yml`, `scripts/setup/init_databases.sh`, `scripts/development/local_mysql.sh`, `reset_database.py`, `export_schema.sh`, `export_openapi.py`, `benchmark_simulation.py`, `backend/pyproject.toml`, `backend/alembic.ini`, `backend/app/core/config.py`, `backend/app/seed.py`, `backend/app/jobs/check_overdue_orders.py`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/playwright.config.ts`, `frontend/e2e/support/env.ts`, `Makefile`. Commands are for macOS and Linux with a POSIX shell; paths are relative to the repository root unless a `cd` is shown.

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12 or later | `requires-python = ">=3.12"`; the code uses PEP 695 generics (`def assert_transition[S]`) and `enum.StrEnum`. |
| uv | current | Installs dependencies into `backend/.venv` from `uv.lock` and runs every backend command (`uv run ...`). Install from https://docs.astral.sh/uv/. |
| Node.js | 20 or later | Required by Vite 7, Vitest 3, and ESLint 9. |
| pnpm | current | `frontend/pnpm-lock.yaml` is the lock file. Enable with `corepack enable pnpm` or install separately. |
| MySQL 8 server | 8.0.14 or later (8.4 recommended) | Query 06 uses LATERAL derived tables (8.0.14+); `docker-compose.yml` pins `mysql:8.4`. Either a local `mysqld` binary (Homebrew `brew install mysql`, or the Anaconda distribution) run through `scripts/development/local_mysql.sh`, or Docker with Compose. |
| MySQL client tools | matching | `mysql` and `mysqladmin` are used by the scripts; `mysqldump` by `export_schema.sh`. |

Optional: `lsof` (used by `local_mysql.sh` to detect a busy port; present on macOS and most Linux distributions).

## 1. Clone and configure the environment

```bash
cp .env.example .env
```

Edit `.env`. Every variable:

| Variable | Default in `.env.example` | Read by | Meaning |
|----------|---------------------------|---------|---------|
| `MYSQL_HOST` | `127.0.0.1` | backend, Alembic, `export_schema.sh` | Host of the MySQL server. The `mysql` client also reads this variable from the environment (see Troubleshooting). |
| `MYSQL_PORT` | `3306` | backend, Alembic, `local_mysql.sh`, `docker-compose.yml`, `export_schema.sh` | TCP port. Use `3307` if a system MySQL already listens on 3306. |
| `MYSQL_DATABASE` | `factory_sherlock` | backend, Alembic, setup scripts | Application schema. The test schema is this name plus `_test`. |
| `MYSQL_USER` | `sherlock_app` | backend, Alembic, setup scripts | Least-privilege application user created by `init_databases.sh`. |
| `MYSQL_PASSWORD` | `change-me` | backend, Alembic, setup scripts | Password of the application user. |
| `MYSQL_ROOT_PASSWORD` | `change-me-root` | `docker-compose.yml` only | Root password of the Docker MySQL container. Not read by the application; the local script initialises root without a password. |
| `JWT_SECRET_KEY` | placeholder | backend | HS256 signing key. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Login fails with a 500 `InternalError` if it is empty. |
| `JWT_ACCESS_TOKEN_MINUTES` | `120` | backend | Token lifetime. |
| `LOGIN_MAX_FAILURES` | `5` | backend | Failed logins allowed per username and per client address before `POST /auth/login` returns 429. |
| `LOGIN_WINDOW_SECONDS` | `900` | backend | Length of the sliding window for `LOGIN_MAX_FAILURES`. Counted in memory per API process. |
| `SEED_DEMO_PASSWORD` | `change-me-demo` | `app.seed` | Password for the four demo accounts (`admin`, `engineer`, `operator`, `viewer`). The seed refuses to run without it. |
| `CORS_ORIGINS` | `http://localhost:5173` | backend | Comma-separated browser origins allowed to call the API. |
| `APP_ENV` | `development` | backend, Alembic, reset script | `development`, `test`, or `production`. `test` switches every tool to `<MYSQL_DATABASE>_test`. |
| `LOG_LEVEL` | `INFO` | backend, seed | Root logger level for the JSON log output. |

The backend reads the repository root `.env` first and a `.env` in the current directory second (the latter overrides). `.env` is git-ignored; never commit it.

## 2. Start MySQL

Choose one of the two options.

### Option A: local MySQL binary without Docker

```bash
scripts/development/local_mysql.sh init     # first time only
scripts/development/local_mysql.sh status
```

`init` creates a private data directory under `.local/mysql/` (git-ignored), initialises it with `mysqld --initialize-insecure` (root without a password, bound to `127.0.0.1` only), starts the server on `MYSQL_PORT`, and runs `scripts/setup/init_databases.sh` over the Unix socket to create `MYSQL_DATABASE`, `MYSQL_DATABASE_test`, and the application user with grants on those two schemas only. The server is started with `utf8mb4`, `utf8mb4_0900_ai_ci`, and strict SQL mode. Subsequent sessions:

```bash
scripts/development/local_mysql.sh start
scripts/development/local_mysql.sh stop
scripts/development/local_mysql.sh shell    # mysql client as the application user
```

### Option B: Docker Compose

```bash
docker compose up -d mysql
docker compose ps        # wait until the healthcheck reports healthy
```

The compose file starts `mysql:8.4` with `MYSQL_ROOT_PASSWORD` from `.env`, publishes `MYSQL_PORT` (default 3306) on `127.0.0.1` only, and uses the same character set and SQL mode as the local script. It does not pass the whole `.env` into the container: it sets only `MYSQL_ROOT_PASSWORD`, the application values as `APP_DB_NAME`, `APP_DB_USER`, and `APP_DB_PASSWORD` (never `MYSQL_DATABASE` or `MYSQL_USER`, which would make the image create the user with `GRANT ALL`), and `MYSQL_ROOT_ARGS` and `MYSQL_CLIENT_ARGS` so the mounted `./scripts/setup/init_databases.sh` (`/docker-entrypoint-initdb.d/01_init.sh`) can reach the entrypoint's temporary server over its local socket. The healthcheck pings over TCP on `127.0.0.1`, which only answers after the init scripts have finished, so `healthy` means the databases and user exist. Docker is not installed on the machine this project was developed on, so this path is verified in GitHub Actions instead: the `Compose Smoke` workflow (`.github/workflows/compose-smoke.yml`) runs on every push and pull request that changes `docker-compose.yml`, `scripts/setup/`, `.env.example`, or the workflow itself. It builds `.env` from `.env.example`, runs `docker compose up -d --wait mysql`, checks as root inside the container that both schemas exist with collation `utf8mb4_0900_ai_ci` and that `SHOW GRANTS FOR 'sherlock_app'@'%'` returns exactly the grants written by `init_databases.sh`, then connects as the application user over TCP from the runner, runs `SELECT 1` against both schemas, checks that `SHOW DATABASES` lists only those two plus `information_schema` and `performance_schema`, and checks that `SELECT COUNT(*) FROM mysql.user` is denied. The first run happens when the branch that adds the workflow is pushed; its run id will be recorded here once it is available. If the automatic initialisation does not run, create the schemas and the user manually after the container is healthy:

```bash
set -a; source .env; set +a
MYSQL_ROOT_ARGS="-uroot -p${MYSQL_ROOT_PASSWORD}" \
MYSQL_CLIENT_ARGS="--protocol=tcp --host=127.0.0.1 --port=${MYSQL_PORT}" \
bash scripts/setup/init_databases.sh
```

`init_databases.sh` is idempotent and clears `MYSQL_HOST`, `MYSQL_TCP_PORT`, `MYSQL_UNIX_PORT`, and `MYSQL_PWD` from its own environment so the client connects where the arguments say.

## 3. Install backend dependencies and run migrations

```bash
cd backend
uv sync                        # creates .venv from uv.lock
uv run alembic upgrade head    # creates the 17 tables in MYSQL_DATABASE
```

Alembic reads the connection URL from the application settings (`migrations/env.py`), so it always targets the database the backend will use. There are two migrations, applied in order by `alembic upgrade head`: `migrations/versions/20261104_0106_create_manufacturing_schema.py` (revision `3a5e982c3679`, the 17 tables) and `migrations/versions/20261107_2106_link_alerts_to_production_orders.py` (revision `383273c26ef7`, which adds `alerts.production_order_id` with its index and foreign key). Both have a working `downgrade()`.

## 4. Seed reference data and the demo scenario

```bash
cd backend
uv run python -m app.seed            # products, specifications, machines, defect types, material lots, demo accounts
uv run python -m app.seed --demo     # also runs database/seeds/demo_scenario.json
```

The seed applies `database/seeds/01_reference_data.sql` (idempotent `INSERT ... ON DUPLICATE KEY UPDATE`), creates or re-passwords the demo accounts from `SEED_DEMO_PASSWORD`, and with `--demo` runs the default simulation (seed 42, 12 batches of 20 units per machine, tool wear on CNC-03 from batch index 4, downtime on CNC-02 at batch index 6). Running `--demo` again adds a second run with order numbers prefixed `SIM0010` (the tag counts existing orders); use the reset script for a clean state.

## 5. Run the backend

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000 --no-proxy-headers
```

`--no-proxy-headers` makes uvicorn keep the TCP peer as `request.client` instead of rewriting it from `X-Forwarded-For`. The login throttle counts failures per client address, and uvicorn's default trusts that header from loopback, which is where the Vite proxy connects from. See `SECURITY.md`, "Login throttling".

- API root: `http://127.0.0.1:8000/api/v1`
- Interactive docs: `http://127.0.0.1:8000/api/docs`
- Health: `curl http://127.0.0.1:8000/api/v1/health` returns `{"status":"ok","database":"ok"}`
- Login: `curl -X POST http://127.0.0.1:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"engineer","password":"<SEED_DEMO_PASSWORD>"}'`
- Import inspections from a CSV file (token of an operator, engineer, or admin in `$TOKEN`; the `type=` suffix is needed because curl otherwise sends `application/octet-stream`). The sample file expects the batch described in `docs/quality/inspection-import.md` to exist first:

```bash
curl -X POST http://localhost:8000/api/v1/inspections/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@database/seeds/sample_inspection_import.csv;type=text/csv"
```

Logs are single-line JSON on stdout.

## 6. Run the frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Vite serves `http://localhost:5173` and proxies `/api` to `http://127.0.0.1:8000`, so the backend must be running. Other scripts: `pnpm build`, `pnpm preview`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm test:e2e` (section 10), `pnpm format`. The application has a screen for each route (login, overview, machines, orders, batches, inspections with the CSV import panel, traceability, investigations and the investigation detail case board, analytics with the control chart and the SQL explorer, simulation). List screens read the page envelope (`items`, `total`, `limit`, `offset`) that the paginated endpoints return.

## 7. Reset the database

```bash
cd backend
uv run python ../scripts/development/reset_database.py --demo
```

The script must run from `backend/` through `uv` because it imports `app.core.config`. It drops every table in the configured database with foreign key checks disabled, runs `alembic upgrade head`, and runs the seed (with `--demo` when given). It never touches users, grants, or other schemas. Prefix with `APP_ENV=test` to reset the test database instead.

## 8. Export the schema snapshot

```bash
scripts/development/export_schema.sh
```

Sources `.env`, runs `mysqldump` over TCP against `MYSQL_HOST:MYSQL_PORT` with the application user, and writes DDL only (no data, no auto-increment counters) to `database/schema/schema.sql`. The migration remains the source of truth; the snapshot is for reading.

## 9. Export the OpenAPI document

```bash
cd backend
uv run python ../scripts/development/export_openapi.py
```

Writes `docs/api/openapi.json` from the FastAPI application. Regenerate after any change to routes or schemas; do not edit the JSON by hand.

## 10. Run checks and tests

```bash
cd backend
uv run ruff check . && uv run ruff format --check . && uv run mypy app
APP_ENV=test uv run pytest
cd ../frontend
pnpm lint && pnpm typecheck && pnpm test
```

See `docs/testing/testing-strategy.md` for the test layout and database isolation. `make lint`, `make test-backend`, `make test-frontend`, and `make check-docs` wrap the commands above.

End-to-end browser tests (Playwright Test) live in `frontend/e2e` and need MySQL with the demo scenario loaded (`make seed-demo`, or `make reset-demo` for a clean state):

```bash
cd frontend
pnpm exec playwright install chromium   # once
pnpm test:e2e
pnpm test:e2e:report                    # HTML report of the last run
```

`frontend/playwright.config.ts` starts the servers itself: the backend with `uv run uvicorn app.main:app --host 127.0.0.1 --port 8013 --no-proxy-headers` (from `backend/`) and the Vite dev server on port 5183 with its `/api` proxy pointed at port 8013 (`VITE_API_PROXY_TARGET`), so a development session on ports 8000 and 5173 is not disturbed. Locally a server already listening on 8013 or 5183 is reused; with `CI=1` fresh servers are always started. The password of the demo accounts comes from `E2E_PASSWORD` when set, otherwise from `SEED_DEMO_PASSWORD` in the repository `.env` (`frontend/e2e/support/env.ts`); it is never printed or written to the report. Each run leaves one closed investigation and one quarantined material lot behind; `make reset-demo` restores the demo state. `frontend/e2e/README.md` lists the variables (`E2E_BASE_URL`, `E2E_API_PORT`, `E2E_BROWSER_CHANNEL`, `CI`) and what the tests assume about the demo data. In CI the `End-to-End` workflow (`.github/workflows/e2e.yml`) runs the same command against a MySQL 8.4 service container.

## 11. Render the Mermaid diagrams

```bash
make render-diagrams
```

Runs `scripts/development/render_diagrams.py` from `backend/` with the `docs` dependency group (Playwright). The script loads Mermaid from a CDN, so it needs network access, and drives an installed Google Chrome on macOS or otherwise Playwright's bundled Chromium (`cd backend && uv run --group docs playwright install chromium` once). It writes one `<name>.svg` next to each `.mmd` file in `docs/media/diagrams/`.

```
make render-figures
```

Runs `scripts/development/render_milestone_figures.py` the same way and writes one PNG per Mermaid block in `docs/milestones/*.md` to `docs/milestones/figures/`, which `docs/milestones/build_documents.py` embeds in the DOCX and PDF versions of the milestone documents (the draft ERD in the Week 8 proposal).

## 12. Benchmark simulation persistence

```bash
make benchmark-sim
```

Runs `scripts/development/benchmark_simulation.py` from `backend/`. It needs a migrated and seeded database (reference data is enough) and times `simulation_service.run_simulation`, the function behind `POST /api/v1/simulation/runs`, for two request shapes: the demo scenario (3 machines x 12 batches x 20 units) and a large one (3 x 40 x 50, 6000 units and 12000 inspections). Each shape runs three times inside a session that is rolled back, so no rows are left behind (only the InnoDB auto-increment counters advance). The output is one table with the shape, unit and inspection counts, median seconds for the service call, median seconds for the engine alone, and rows per second (units plus inspections over the median service time). The script refuses to run when `APP_ENV=production`. The figures recorded for the switch to bulk inserts are in `docs/simulation/simulation-design.md`.

## 13. Raise overdue order alerts

```bash
make check-overdue
```

Equivalent to `cd backend && uv run python -m app.jobs.check_overdue_orders`; add `--as-of 2026-11-07T08:00:00` to judge due dates against another moment. The job raises one `ORDER_OVERDUE` alert per `PLANNED`, `RELEASED`, or `IN_PROGRESS` order whose `due_date` is before the check date and that has no unacknowledged overdue alert yet (`alert_service.raise_overdue_order_alerts`, rules BR-100 to BR-104 in `docs/requirements/business-rules.md`), commits, logs `checked`, `raised`, and `alert_ids` as one JSON line, and exits 0. It is idempotent, so a scheduler can run it as often as wanted. The same check is available to operators, engineers, and admins as `POST /api/v1/analytics/alerts/checks/overdue-orders` with an optional `{"as_of": "..."}` body. On the demo data the order that query 02 labels `OVERDUE` (the CNC-02 order left `IN_PROGRESS` by the simulated downtime) is the one that receives an alert.

## Troubleshooting

Port 3306 is already in use. A system MySQL (Homebrew service, Anaconda, or another container) often owns 3306. `local_mysql.sh start` detects this with `lsof` and refuses to start. Set `MYSQL_PORT=3307` in `.env`; the backend, Alembic, the scripts, and Docker Compose all read the same variable.

The `mysql` client connects to the wrong server. The `mysql` command-line client honours `MYSQL_HOST`, `MYSQL_TCP_PORT`, `MYSQL_UNIX_PORT`, and `MYSQL_PWD` from the environment. After `source .env`, a bare `mysql -uroot` may connect to the host named in `.env` rather than the socket or port you intended. `init_databases.sh` unsets these variables for that reason. When running the client by hand, pass `--host`, `--port`, and `--protocol=tcp`, or `--protocol=socket --socket=.local/mysql/mysql.sock`, explicitly, or use `scripts/development/local_mysql.sh shell`.

Anaconda `mysqld` fails to start or cannot find plugins or error messages. The Anaconda distribution does not locate its own `lib/plugin` and `share/mysql` directories. `local_mysql.sh` derives `--plugin-dir` and `--lc-messages-dir` from the `mysqld` binary's prefix (`layout_args`) and passes them on both `init` and `start`; nothing further is needed. If you run `mysqld` manually, pass those two options yourself.

`Data directory exists` on `init`. The data directory `.local/mysql/data` already exists. Either run `start` instead or remove `.local/mysql` to re-initialise (this destroys the local databases).

`Missing .env`. Copy `.env.example` to `.env` first; both scripts refuse to run without it.

`SEED_DEMO_PASSWORD is not set; refusing to create accounts`. Set the variable in `.env` before seeding.

Login returns 500 `InternalError`. `JWT_SECRET_KEY` is empty; `create_access_token` raises `RuntimeError`. Set the key and restart uvicorn (settings are cached per process).

`No available material lots for product ...` on `POST /simulation/runs`. Every product needs at least one `AVAILABLE` lot of its material (`PRODUCT_MATERIALS` in `simulation_service.py`). Quarantining all lots of a material, or adding a product that is not in that map, blocks simulation. Receive a new lot through `POST /material-lots` or reset the database.

503 `DatabaseUnavailable`. MySQL is not reachable at `MYSQL_HOST:MYSQL_PORT` with the configured credentials. Check `local_mysql.sh status` or `docker compose ps`, then `.env`.

`Access denied for user 'sherlock_app'`. The user or grants were not created (for example, the Docker initialisation did not run) or `MYSQL_PASSWORD` differs from the one used at creation. Re-run `init_databases.sh`; it is idempotent but does not change an existing user's password, so drop and recreate the user if the password changed.

Tests touch development data. Export `APP_ENV=test` before `pytest`, `alembic`, or `reset_database.py`; verify with `uv run python -c "from app.core.config import get_settings; print(get_settings().effective_database)"`, which must print `factory_sherlock_test`.

`uv: command not found` or wrong Python. Install uv and run `uv python install 3.12` if no suitable interpreter is found; `uv sync` selects an interpreter satisfying `>=3.12`.

Frontend cannot reach the API. The Vite proxy targets `127.0.0.1:8000`; start uvicorn on that port. If you call the API directly from another origin, add it to `CORS_ORIGINS`.
