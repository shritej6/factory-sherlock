# Factory Sherlock frontend

Web interface for the Factory Sherlock manufacturing simulation, quality control, and defect investigation platform. It talks to the FastAPI backend under `/api/v1`.

## Stack

React 19, TypeScript (strict), Vite 7, Tailwind CSS 4, React Router 7, TanStack Query 5, Recharts 3, Vitest with React Testing Library, ESLint (typescript-eslint), Prettier, pnpm.

## Commands

Run these from `frontend/`.

| Command          | What it does                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------- |
| `pnpm install`   | Install dependencies                                                                          |
| `pnpm dev`       | Start the dev server on http://127.0.0.1:5173 with `/api` proxied to the backend on port 8000 |
| `pnpm lint`      | ESLint, zero errors expected                                                                  |
| `pnpm typecheck` | `tsc --noEmit` for the app and the Vite config                                                |
| `pnpm test`      | Vitest, jsdom environment                                                                     |
| `pnpm build`     | Type check then production build into `dist/`                                                 |
| `pnpm preview`   | Serve the production build locally                                                            |
| `pnpm format`    | Prettier                                                                                      |

The backend must be running for the app to do anything useful:

```
cd ../backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Sign in with one of the seeded accounts (`admin`, `engineer`, `operator`, `viewer`). The password is the `SEED_DEMO_PASSWORD` value in the repository `.env` file and is never stored in the frontend source.

## Structure

```
src/
  app/          router, providers, query client, layout, sidebar, auth guard
  components/   ui (buttons, panels, fields, tables, badges, SQL disclosure, states)
                charts (Recharts wrappers with a shared frame)
  features/     one folder per screen: login, overview, machines, orders, batches,
                quality, investigations, traceability, analytics, simulation
  hooks/        auth context and provider, TanStack Query hooks and keys
  services/     typed fetch client (http.ts) and endpoint modules (api.ts)
  types/        API types mirrored from the OpenAPI contract, enums and defaults
  utils/        error mapping, permissions, state machines, formatting, chart transforms
  styles/       Tailwind entry and design tokens (light theme with dark-mode overrides)
tests/          Vitest setup and shared render helpers
```

Tests live next to the code as `*.test.ts(x)`.

## What is implemented

Screens, all behind login:

1. Login: username and password, API error messages shown inline. A 429 shows the wait from `details.retry_after_seconds` ("Too many attempts. Try again in N seconds.") and falls back to the backend message when the field is absent.
2. Factory Overview: machine status cards, quality tiles from `/quality/summary`, active order count from `/production-orders/status-counts`, recent alerts with acknowledge, open investigation count from a status-filtered total.
3. Machine Monitoring: machine list, event timeline, change-status form that offers only the transitions the backend allows, per-machine quality summary.
4. Production Orders: table with status filter, create form, transition buttons limited to legal moves (Planned to Released or Cancelled, Released to In progress or Cancelled, In progress to Completed or Cancelled), edit for Planned and Released orders.
5. Production Batches: table with order, machine, and status filters applied by the server, create form with material lot lines, complete and quarantine actions. Each row carries `order_number`, so the table needs no second lookup of orders.
6. Quality Inspection: inspection table with result and batch filters and defect code chips, record inspection form, defect-rate-by-machine chart.
7. Investigations: list, open form (title, machine, window), and a case board with the summary, one evidence card per rule R1 to R6 (rule code, title, narrative, result table, and a "Show the SQL" disclosure with the query name and exact SQL), status actions (mark in review, return to open, close with a required conclusion), and flagged batches with a link into the batch table.
8. Material Traceability: forward trace by lot number, backward trace by serial number, quarantine a lot with a reason.
9. Analytics and Reports: daily production trend, defect rate by machine, pass and fail distribution, defect categories, orders by status, plus an SQL Explorer that lists every documented query from the catalog. Runnable dashboard queries execute with the parameters they bind (window, machine, threshold, hours, limit) and show the rows and SQL; traceability and investigation queries are shown read-only with their SQL and a note on where they run.
10. Simulation: form bound to `SimulationRequest` with a fault scenario builder and a result summary.

Role handling mirrors the backend route guards: viewers see read-only screens; operators can change machine status, move orders between states, start and complete batches, record inspections, and acknowledge alerts; engineers and administrators can do everything else. Controls the current role cannot use are hidden or replaced with a short explanation.

Every chart has a "View data table" disclosure beneath it with the plotted rows, so the figures are readable without the graphic.

Every data view has loading, empty, and error states. API errors use the backend envelope (`error`, `message`, `details`, `request_id`). Queries that fail render `ErrorState` (message, request id, retry button); mutations and row actions render `ErrorNotice` from `components/ui/States.tsx`, which shows the same message and request id inline, so a failure can always be quoted with its backend correlation id. Components keep the raw error (`unknown`) in state and hand it to these two components rather than storing a formatted string. A 401 or 403 on session restore clears the session and returns to the login screen; a network or server error keeps the stored token and shows a "Could not verify the session" panel with a retry. Cached data is cleared on sign in and sign out so one user never sees another user's lists.

Status filters are applied by the API, not by the page. `GET /production-batches` and `GET /investigations` accept a repeatable `status` parameter (`status=A&status=B`, any of them), and `buildQuery` in `services/http.ts` sends an array value as repeated keys. The batch table filters by one status, the Overview counts `OPEN` and `IN_REVIEW` cases from the `total` of a one-row filtered page (`useOpenInvestigationCount`), and the batch form lists only `RELEASED` and `IN_PROGRESS` orders (`useProducibleOrders`, one request per status because the order list filters by a single status).

Order counts come from `GET /production-orders/status-counts`, one integer per order status, through `useOrderStatusCounts` in `hooks/queries.ts`. The Overview sums `RELEASED` and `IN_PROGRESS` for the active order tile and the Analytics page draws the orders-by-status chart from the same response. The key shares the `orders` root, so any production mutation refreshes it.

The control chart (query 10, `characteristic_control_chart`) returns `ucl` and `lcl` per subgroup: `grand_mean` plus or minus three pooled standard deviations divided by the square root of that subgroup's `sample_count`, so small subgroups get wider limits. `toControlChartSeries` in `utils/chartTransforms.ts` reads the limits from each row, marks a point out of control against its own limits, and the chart draws them as stepped lines (`type="stepAfter"`) around a straight grand mean reference line. `grand_mean`, `target_value`, and the specification limits are constant for the response and are read once.

Accessibility: a "Skip to content" link is the first focusable element, the document title and keyboard focus follow the page heading on every route change, the mobile navigation drawer is inert when closed and closes on Escape, charts have data table alternatives, and colours meet WCAG 2.1 AA contrast in the light theme.

Default analytics and investigation windows are 2026-11-01 to 2026-11-05 because the seeded demonstration data is dated 2026-11-02 (one production day, 06:00 to 12:00). The windows are editable on every screen that uses them.

## Not included

There is no screen for creating products, machines, or material lots. Browser tests live in `e2e/`; see `e2e/README.md`.
