# End-to-end tests

Browser tests written with Playwright Test. They drive the real frontend against the real backend and MySQL, signed in with the seeded demo accounts, and cover the demo workflows: login, opening and closing an investigation, forward and backward traceability with a lot quarantine, role gating for the viewer, and the SQL explorer.

## How to run

Prerequisites: MySQL running with the demo scenario loaded (`make migrate` and `make seed-demo`, or `make reset-demo`), `uv` for the backend, and the Playwright Chromium build:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm exec playwright install chromium   # once
pnpm test:e2e                           # run the suite
pnpm test:e2e:report                    # open the HTML report of the last run
```

`playwright.config.ts` starts both servers itself: the backend with `uv run uvicorn app.main:app --port 8013` (from `backend/`) and the Vite dev server on port 5183 with its `/api` proxy pointed at port 8013 (`VITE_API_PROXY_TARGET`). Locally a server already listening on those ports is reused; in CI (`CI=1`) the config always starts fresh ones. The default development ports 8000 and 5173 are not touched, so the suite can run next to a normal development session.

Environment variables:

| Variable              | Default                 | Purpose                                                                    |
| --------------------- | ----------------------- | -------------------------------------------------------------------------- |
| `E2E_BASE_URL`        | `http://localhost:5183` | Frontend address; its port is also the port Vite is started on             |
| `E2E_API_PORT`        | `8013`                  | Port of the backend started for the run                                    |
| `E2E_PASSWORD`        | unset                   | Password of the demo accounts; CI sets it                                  |
| `E2E_BROWSER_CHANNEL` | unset                   | Set to `chrome` to run the installed Google Chrome instead of the download |
| `CI`                  | unset                   | Enables one retry, fresh servers, and `forbidOnly`                         |

When `E2E_PASSWORD` is not set, the config reads `SEED_DEMO_PASSWORD` from the repository `.env`, the same value `uv run python -m app.seed --demo` used for the accounts. No password is committed or printed.

Single test or file: `pnpm test:e2e e2e/login.spec.ts`, `pnpm test:e2e -g "viewer"`. Headed debugging: `pnpm test:e2e --headed` or `pnpm test:e2e --ui`. Traces are recorded on the first retry (CI) without the spec sources and are viewable from the HTML report in `playwright-report/`, which is ignored by Git together with `test-results/`.

Credentials and traces: a trace records typed values and request bodies, so the shared `signIn` helper in `e2e/support/auth.ts` does not type the password. It obtains a token from `/auth/login` with Node's `fetch`, outside the browser, stores it where the app keeps its session, and waits for the overview heading or the first alert, failing with the alert text. Only `login.spec.ts` types the password into the form, and that file runs with tracing off.

## What the tests assume about the demo data

The tests run against `database/seeds/demo_scenario.json` as loaded by `app.seed --demo` (seed 42):

- Machines `CNC-01`, `CNC-02`, `CNC-03`; `CNC-03` develops tool wear from its fifth batch, so an investigation on it for the production day from 06:00 to 12:00 reports an elevated defect rate, produces evidence cards `R1` to `R6`, and flags batches. The date of that day is read from the first `CNC-03` batch through the API, not hard-coded.
- Material lot `L201` (steel bar stock) is consumed by `CNC-03` batches; the forward trace lists them and the backward trace of `<first batch>-U0001` lists `L201` and an inspection summary.
- Lots `L301` to `L303` (`CNC-02`) and `L401` to `L403` (`CNC-01`) are `AVAILABLE`; the quarantine test picks the first of them that is still available and whose batches do not involve `CNC-03`.
- `batches_requiring_review` with the default window (2026-11-01 to 2026-11-05) and threshold 0.10 returns at least one row, which holds while the `CNC-03` batches are not quarantined.
- The demo accounts `engineer` and `viewer` exist with the seeded password.
- The traceability tests check through the API that lot `L201` exists before tracing it, so a missing seed fails with a message naming the lot rather than with a table timeout.

Each test signs in on its own and does not depend on another test having run. Files run in parallel; the tests within a file run in order.

## Data the suite leaves behind

The suite does not clean up after itself; the demo database is a seeded development database and the changes are small and visible:

- Every run opens one investigation titled `E2E CNC-03 tool wear <timestamp>` and closes it with a conclusion. Closed cases stay in the list.
- Every run quarantines one material lot (and the batches that consumed it) from `L301` to `L303` and `L401` to `L403`. After six runs none of them is `AVAILABLE` and the quarantine test fails with a message saying so.

To start from a clean demo database run `make reset-demo` (which drops all tables, migrates, and seeds again) and run the suite again. Nothing the suite writes touches `CNC-03` batches or the `L2xx` lots, so the investigation evidence stays the same from run to run until the database is reset.

## Continuous integration

`.github/workflows/e2e.yml` ("End-to-End") starts a MySQL 8.4 service, migrates and seeds the demo scenario, installs the Playwright Chromium build, and runs `pnpm test:e2e` with `CI=1` and `E2E_PASSWORD` set to the throwaway demo password written to the CI `.env`. The HTML report is uploaded as an artifact when the job fails.
