# Conversation 7: Parallel review passes and the fix wave

Project area: backend security and error handling, CSV import, alerts, SQL and indexes, frontend. Tool: Claude Code. Date: 2026-11-07.
Outcome: five independent review passes produced 60 findings; the ones that changed behaviour were fixed on six branches, each with its own test database, and merged after the full gate set.

## Sequence

1. Context: after the nine roadmap features were integrated (conversation 6), five review passes ran at the same time on the integration branch, each with one lens: code quality, security, performance, error handling, database design. Each reviewer wrote findings with file and line references, a severity, and a proposed fix. Duplicates across passes were kept as evidence that a finding was independently confirmed.
2. The findings were grouped by the files they touched so that the fixes could be written in parallel without merge conflicts: authentication and error mapping; CSV import and request body caps; overdue alerts; SQL, migration and database documents; API additions; frontend consumers. Every fix branch started from the same commit, used its own MySQL database (fs_w01 to fs_w06) and had to pass ruff, ruff format, mypy, the full pytest suite, ESLint, tsc, Vitest, the production build and the documentation check before it was accepted.
3. The highest-severity finding, confirmed by three passes, was the login throttle checking the client address before the password: behind the Vite development proxy every browser shares one address, and uvicorn trusts X-Forwarded-For from loopback by default. The redesign and its tests are in row 44 of the AI use record.
4. Two findings changed data correctness rather than security: the control chart computed one pair of control limits from the average subgroup size (row 48), and MySQL CHECK constraint violations were reported as an unreachable database (row 45).
5. Three findings were about scale: the import wrote one row at a time (row 46), the list endpoints sorted without a matching index (row 48), and the frontend made six requests to count orders and filtered 500-row lookups in the browser (row 49).
6. One finding was about trust: the overdue check accepted a client-chosen date (row 47).
7. Integration: the six branches merged with two textual conflicts (an import block and a documentation paragraph), both resolved by keeping both sides. After the merge the schema snapshot and the OpenAPI document were regenerated, the local MySQL server was restarted with the default sql_mode, and the end-to-end suite found that the accessibility pass had renamed two landmarks that two specs depended on (row 50).

## Verification

- Every fix branch: full backend suite against its own test database (between 381 and 472 tests at the time of each run), ruff, mypy strict, and for frontend changes ESLint, tsc, Vitest, and the production build.
- Integration branch after all merges: 481 backend tests, 118 Vitest tests in 25 files, 9 Playwright tests, `alembic check` with no drift, `make check-docs` clean.
- Throttle: the regression test logs in as a second user from the same address after five failures by the first; a twenty-thread test admits exactly five concurrent checks.
- Import: scripts/development/benchmark_inspection_import.py, 5000 rows, median of three, before and after figures recorded in docs/quality/inspection-import.md.
- Control chart: a one-hour window on the demo data shows different limits for subgroups of 1, 19 and 20 samples; the integration test asserts that the half-width times the square root of the sample count is constant.
- Indexes: EXPLAIN on the demo database and on a grown copy (49,400 and 241,400 inspections) is recorded in docs/database/database-design.md section 6; the migration was downgraded and upgraded twice.
- Overdue alerts: a thread with its own session blocks on the locked rows and raises nothing after the first check commits.

## Student annotation

[Shritej: write in your own words which of the review findings you consider the most important for the course, why the reviewers found the throttle problem when the feature tests had passed, and what you would add to the test plan so a finding of that kind is caught before review.]
