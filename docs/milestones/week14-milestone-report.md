# Week 14 Milestone Report: Testing and Release Readiness

**Course:** CS3320 Database Systems, Instructor Dr. Chibuzo Ukegbu
**Student:** Shritej Gunda (individual project)
**Project:** Factory Sherlock: Manufacturing Simulation, Quality Control, and Defect Investigation on MySQL
**Date:** [submission date]
**Repository:** https://github.com/shritej6/factory-sherlock
**Commit or tag:** branch feature/completion-integration, pushed 2026-11-08; the first green runs of all five workflows are on commit 0de489b (section 2). The release candidate tag is planned as v1.0.0-rc1 on the commit that merges feature/completion-integration.

## 1. Completion status, incomplete items, and blockers

The Week 14 row of docs/milestones/README.md lists eight required artifacts; the walkthrough video from the media plan is the ninth item. Status on the integration branch (head c978744) on 2026-11-07:

| Item | Status | Evidence |
|---|---|---|
| Release candidate | Complete on the branch, tag pending | feature/completion-integration holds every feature and fix merge since the first push on 2026-11-04; five GitHub Actions workflows; all local gates pass (section 2). Tag v1.0.0-rc1 is [to be created after the merge to main]. |
| Completed test matrix | Complete | docs/testing/test-matrix.md (TM-01 to TM-34, one row per behaviour and one per Playwright spec) and testing-strategy.md were rewritten on 2026-11-07 from the suite runs in section 2; every cited test name was checked against backend/tests and frontend/src. |
| Defect and fix evidence | Complete | Nine review and fix reports from the final wave, condensed in section 2; every named test exists in the worktree. |
| Final ERD and schema | Complete | docs/media/diagrams/er-diagram.svg; database/schema/schema.sql regenerated in c978744; three migrations with downgrades. |
| Tested README | Complete | README commands executed in this worktree (section 2); the stale statements found during that run were corrected the same day (commit 9e7cd7a). |
| Demo data | Complete | make reset-demo against database fs_w08 on 2026-11-07; counts in section 2. |
| Report draft | Complete, student sections pending | This document plus docs/milestones/week12-milestone-report.md and week13-milestone-report.md; the bracketed prompts in sections 4, 6, 8 and 9 of each are for the student. |
| AI evidence package | Complete, student annotations pending | docs/ai_evidence: README, ai-use-record.md (51 rows), seven conversation records, reflection-notes.md. |
| Walkthrough video and screenshot refresh | Complete for the silent clips, narration pending | Fourteen screenshots re-captured on 2026-11-07 (docs/media/screenshots, 1.75 MB), five of them new: CSV import result, control chart, batch status filter, overdue check, throttled login. Videos 2 to 6 recorded as silent 1280 by 800 clips by scripts/development/record_walkthroughs.py and committed under ADR-0010 (docs/media/videos, 10.4 MB). Video 1 (slides) and the narration are the student's recording work. |

Blockers: none that stop the submission. Open risks are the narration of videos 2 to 6 and the slides for video 1. The first GitHub Actions runs of all five workflows, including Compose Smoke and End-to-End, passed on 2026-11-08 (section 2). [Add any blocker you see, or write "none".]

## 2. Required technical artifacts and repository commit or tag

### Release candidate

Branch feature/completion-integration, head c978744 (chore: regenerate schema and OpenAPI exports). The merge commits name each feature and the six fix merges of the final wave (0ffdf3e, ae949eb, 758b4e6, 5fcdebf, 9325d87, 582c360).

| Workflow | File | Checks | First run on the pushed branch (2026-11-08) |
|---|---|---|---|
| Backend CI | backend-ci.yml | Against a mysql:8.4 service: init_databases.sh, alembic upgrade head, ruff check, ruff format --check, mypy app, pytest with coverage | Passed, run 42568859627 |
| Frontend CI | frontend-ci.yml | pnpm install --frozen-lockfile, eslint, prettier check, tsc on three tsconfigs, vitest, vite build | Passed, run 42568859552 |
| Docs Lint | docs-lint.yml | Fails on em dashes, en dashes, or emoji in Markdown; renders every .mmd diagram with mermaid-cli (allowed to fail) | Passed, run 42568859579 |
| Compose Smoke | compose-smoke.yml | Starts mysql from docker-compose.yml, checks both schemas and the least-privilege grants as root, connects as the application user over TCP, confirms mysql.user is denied | Passed, run 42568859629 |
| End-to-End | e2e.yml | Migrates and seeds a mysql:8.4 service with the demo scenario, installs Chromium, runs the Playwright suite (backend port 8013, Vite port 5183) | Passed, run 42568859641 |

Every gate runs locally from the Makefile: make lint (ruff check, ruff format --check, mypy, eslint, tsc), make test-backend (pytest against the <MYSQL_DATABASE>_test schema), make test-frontend, make check-docs, make migrate, make reset-demo, make export-schema, make export-openapi; the browser suite is pnpm test:e2e in frontend/. Observed in this worktree on 2026-11-07: make lint printed "All checks passed!", "122 files already formatted", and "Success: no issues found in 80 source files", with eslint and tsc clean; make check-docs passed; make test-backend against fs_w08_test printed "481 passed, 1 warning in 222.18s". The Playwright suite passed 9 of 9 locally on 2026-11-07 at commit 11d5c3a (`pnpm test:e2e`, 4.9 s); the End-to-End workflow runs the same suite in CI.

### Completed test matrix

docs/testing/test-matrix.md holds rows TM-01 to TM-34: the twelve required scenarios, one row per behaviour added since Week 10 (pagination, import, body caps, overdue alerts, the control chart, R7, status filters, list ordering indexes, the throttle, frontend accessibility), and one row per Playwright spec, each with Setup, Action, Expected result, Actual result, Status, and Evidence naming the test functions. docs/testing/testing-strategy.md describes the pyramid, the database isolation, the end-to-end layer, the five workflows, and the benchmark scripts. Both were rewritten on 2026-11-07 from these counts:

| Layer | Count | Source |
|---|---|---|
| Backend unit (no database) | 254 cases in 13 modules | uv run pytest --collect-only -q: 481 collected |
| Backend API (TestClient against MySQL) | 174 cases in 16 modules | same collection |
| Backend database integration | 53 cases in 6 modules | same collection |
| Frontend Vitest | 118 tests in 25 files | pnpm -s test |
| Playwright end-to-end | 9 tests in 5 spec files | analytics (1), investigation (1), login (2), roles (2), traceability (3) |

About 53 percent of the backend cases are unit tests and 47 percent run against MySQL 8.4, so constraints, transactions, and the SQL files are exercised on the real server rather than mocked.

### Defect and fix evidence

The final wave produced nine reports (fix reports F1 to F6, the accessibility pass, two documentation passes). Each row names the test that now guards the finding; every name was checked against the worktree.

| # | Finding | Severity | Symptom | Fix | Guarding test |
|---|---|---|---|---|---|
| 1 | Shared address lockout and header spoofing | High | Five wrong passwords from one address locked every account behind the Vite proxy (all browsers arrive from 127.0.0.1); uvicorn trusted X-Forwarded-For from loopback | Account bucket checked first, address bucket only after a failure (401 becomes 429); uvicorn runs with --no-proxy-headers | test_failures_as_one_user_do_not_lock_another_user_from_the_same_address, test_missing_peer_address_is_reported_as_none (backend/tests/api/test_login_throttle_api.py) |
| 2 | Username normalisation | Medium | admin, ADMIN, and an accented spelling had separate buckets although the collation resolves them to one row | Key by user id when known, otherwise NFKD, mark-stripped, casefolded username | test_case_and_accent_variants_count_against_the_same_account (same file) |
| 3 | check/record race | Medium | Requests between check() and record_failure() could all pass the limit | check() reserves a pending slot under the lock | test_concurrent_checks_cannot_exceed_the_limit (20 threads, 5 admitted; backend/tests/unit/test_login_throttle.py) |
| 4 | CHECK constraint mapped to 503 | Medium | MySQL errno 3819 arrives as OperationalError and was answered 503 | classify_operational maps 3819 to 422 with the constraint name, 1406 to 422, connection errors to 503 "not reachable" | test_check_constraint_violation_from_the_database_is_a_422_with_the_constraint_name (backend/tests/api/test_error_contract.py); backend/tests/unit/test_error_mapping.py |
| 5 | Per-row CSV writes | High | record_inspection per row: 10,507 statements, 1.47 s for 5,000 rows | In-memory evaluation, then chunked multi-row INSERTs in a savepoint: 15 statements, 0.11 s (scripts/development/benchmark_inspection_import.py) | test_valid_file_is_imported_with_the_same_rules_as_manual_entry, test_one_invalid_row_rolls_back_the_whole_file (backend/tests/api/test_inspection_import.py) |
| 6 | csv.Error 500 | Medium | An oversized field or text after a closing quote crashed with 500 | parse_csv catches csv.Error and answers 422 with field "file" | test_broken_csv_structure_is_a_file_error_not_a_crash (backend/tests/unit/test_inspection_csv.py) |
| 7 | Import race | Medium | A pair recorded by another request during the import hit uq_inspection_unit_spec without a row-level message | errno 1062 rolls back to the savepoint, re-reads with a locking read, reports the rows as 422; other integrity errors re-raised | test_pair_recorded_by_another_request_during_the_import_is_a_row_error, test_other_integrity_errors_are_not_mistaken_for_the_race (test_inspection_import.py) |
| 8 | Decimal parser | Low | Decimal() accepted 1_000, 2.004e1, and non-ASCII digits | Fullmatch on sign, ASCII digits, at most three decimals before Decimal() | test_bad_measured_values_name_the_row_and_field (parametrised, test_inspection_csv.py) |
| 9 | as_of forgery | Medium | An operator could post {"as_of": ...} to raise alerts early or back-date created_at | The endpoint takes no body and uses the server clock; only the CLI job keeps --as-of | test_client_cannot_choose_the_check_date (backend/tests/api/test_alert_checks_api.py) |
| 10 | Duplicate overdue alerts | Medium | Two overlapping checks could both find no open alert and insert two | SELECT ... FOR UPDATE on the orders and their open alerts | test_concurrent_checks_raise_one_alert_per_order (backend/tests/integration/test_alert_order_link.py) |
| 11 | Job failure handling | Medium | A failure in the job left a bare traceback, no structured log line, no defined exit status | run_check rolls back; main logs under operation=check_overdue_orders and returns 1 | test_job_rolls_back_logs_and_exits_one_on_failure (same file) |
| 12 | Control limits from average sample size | High | Query 10 divided the pooled standard deviation by SQRT(avg_sample_size), so every subgroup got the same limits | Per-row SQRT(sample_count) in database/queries/10_characteristic_control_chart.sql; the chart draws stepped limits | test_control_chart_limits_widen_for_smaller_subgroups (backend/tests/integration/test_queries.py); "judges each subgroup against its own limits" (frontend/src/utils/chartTransforms.test.ts) |
| 13 | Missing list ordering indexes | Medium | Four paginated lists sorted with a filesort over the whole table; query 10 had no index covering both predicates | Migration 6c1f0d2a9b47 adds five indexes | test_list_ordering_indexes_exist_with_time_then_id, test_composite_index_replaces_the_implicit_specification_fk_index (backend/tests/integration/test_list_ordering_indexes.py) |
| 14 | Six-request order count fan-out | Medium | The overview issued one list request per order status to count active orders | GET /production-orders/status-counts from one GROUP BY | test_order_status_counts_match_the_list_totals (backend/tests/api/test_status_filters_api.py); "counts active orders from one status-counts request" (frontend/src/features/overview/OverviewPage.test.tsx) |
| 15 | Client-side filtering over 500 rows | Medium | Batch status filter and open investigation count fetched 500 rows and filtered in the browser | Repeatable status filter in SQL before pagination, so total reflects the filter; order_number joined with selectinload | test_batches_status_total_reflects_filter_before_paging, test_batch_list_loads_order_numbers_without_a_query_per_row (test_status_filters_api.py) |
| 16 | Bare-array tests broken by the pagination envelope | Low | Eight API tests and the e2e helper still read a bare array after six lists moved to {items, total, limit, offset} | Tests read .json()["items"]; the e2e helper requests limit 500 (7bca7ac, a95df14) | test_inspection_import.py and test_alert_checks_api.py pass again; frontend/e2e/investigation.spec.ts |
| 17 | Accessibility contrast and focus | Medium | ink-faint text at 4.42:1 and the request id line at 3.95:1; closing an inline form dropped focus to body; the drawer opened without moving focus | Token shades at 4.5:1 or better, focus returns to the toggle, drawer focuses its first link | "returns focus to the toggle when the form closes itself" (frontend/src/components/ui/Disclosure.test.tsx); "moves focus into the drawer when it opens and back to the menu button on Escape" (frontend/src/app/AppLayout.test.tsx) |
| 18 | Pagination showing an empty range | Low | When the offset ran past the total the table showed an empty page | Pagination clamps to the last page with rows and emits the corrected offset | "clamps back to the last page with rows when the offset runs past the total" (frontend/src/components/ui/Pagination.test.tsx) |

Two corrections landed after the reports: catalog_service converts only errno 1062 to 409 (6635d8a, backend/tests/unit/test_catalog_conflict.py), and the frontend no longer sends a body to the overdue check (1140e0e, "posts without a body" in OverviewPage.test.tsx).

### Final ERD and schema

database/schema/schema.sql was regenerated from the migrated database in c978744: 17 application tables plus alembic_version. Compared with Week 10 it carries alerts.production_order_id with fk_alerts_production_order (ON DELETE SET NULL) and ix_alerts_production_order, and the five indexes from revision 6c1f0d2a9b47: ix_inspections_time_id (inspected_at, id), ix_inspections_spec_time (specification_id, inspected_at), ix_production_batches_started_id (started_at, id), ix_production_orders_created_id (created_at, id), ix_investigations_created_id (created_at, id). The implicit specification_id index on inspections is gone: MySQL drops it when a composite index with the same leading column is created, the upgrade drops it explicitly when MySQL kept it, and the downgrade recreates it before dropping the composite index (error 1553 otherwise). The three migrations in backend/migrations/versions each have a downgrade: 3a5e982c3679 (tables), 383273c26ef7 (alerts.production_order_id), 6c1f0d2a9b47 (indexes). docs/database/database-design.md section 6 records the index rationale with EXPLAIN observations and the lock class of each migration operation. docs/media/diagrams/er-diagram.svg is rendered from er-diagram.mmd, which names production_order_id on alerts.

### Tested README

README.md commands executed in this worktree on 2026-11-07 against the shared local MySQL 8.4.0 server with .env pointing at fs_w08: cd backend && uv sync; uv run alembic upgrade head (383273c26ef7 and 6c1f0d2a9b47 applied on top of 3a5e982c3679); cd frontend && pnpm install --frozen-lockfile; make reset-demo (dropped 18 tables, re-ran the three migrations, seeded the scenario); make lint; make test-frontend; make test-backend; make check-docs; make help. make db-init and make db-start were not run because the shared server was already up; docker compose up was not run because Docker is not installed on this machine (the Compose Smoke workflow covers that path).

That run found README.md statements that no longer matched the code: "Six evidence rules (R1 to R6)" (there are seven), "Twelve SQL files" (there are 14), "31 paths" (openapi.json has 35 paths and 44 operations), the 2026-11-03 test table, "eight records" (nine ADRs), "the compose file has not been executed", "no rate limiting or account lockout", "without pagination", and roadmap items 2 to 6 still listed as open. All of them were corrected in commit 9e7cd7a, which also updated CONTRIBUTING.md, CHANGELOG.md and the development roadmap.

### Demo data

make reset-demo on fs_w08 (2026-11-07, 22:36 UTC) logged seed 42, orders_created 9, batches_created 35, units_created 700, inspections_created 1400, failed_inspections 51, events_created 12, alerts_created 2. Row counts queried afterwards with the mysql client:

| Table | Rows |
|---|---|
| users (demo accounts) | 4 |
| products / product_specifications | 3 / 6 |
| machines | 3 (CNC-01 IDLE, CNC-02 IDLE, CNC-03 WARNING) |
| defect_types / material_lots | 5 / 9 |
| production_orders / production_batches / production_units | 9 / 35 / 700 |
| batch_materials | 47 |
| inspections (FAIL) | 1,400 (51) |
| inspection_defects | 51 |
| machine_events | 12 |
| alerts | 2 (MACHINE_FAULT CRITICAL on CNC-02, HIGH_DEFECT_RATE WARNING on CNC-03) |
| investigations / investigation_evidence / investigation_batches | 0 / 0 / 0 |

The seed opens no investigation; the case board screenshot and the end-to-end spec open one through POST /api/v1/investigations on CNC-03. alembic_version read 6c1f0d2a9b47 and @@sql_mode included ONLY_FULL_GROUP_BY.

### Report draft

This document is the Week 14 draft; the Week 12 and Week 13 reports sit beside it in docs/milestones. All three build to DOCX and PDF with docs/milestones/build_documents.py, which also counts the bracketed prompts that remain for the student.

### AI evidence package

docs/ai_evidence holds README.md (tools, verification approach, honesty rules), ai-use-record.md (43 numbered rows dated 11-03 to 11-07), six conversation records (schema and normalization; simulation state machine revision; rejected Alembic downgrade; ORM aggregation bug; environment and client defaults; parallel feature integration), and reflection-notes.md with the prompts for the Week 8 and Week 15 reflections. The student annotation at the end of each conversation record is still bracketed.

## 3. Decisions, alternatives, assumptions, constraints, and rationale

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Release scope: the functional unique index on open ORDER_OVERDUE alerts was probed and not added | CREATE UNIQUE INDEX over CASE WHEN alert_type = 'ORDER_OVERDUE' AND acknowledged_at IS NULL THEN production_order_id END; MySQL 8.4.0 accepted it on a scratch database and rejected a second open alert with error 1062 | The locking read in alert_service already serialises concurrent checks and is covered by a two-session test; the index would also require the service to treat 1062 on that key as "already raised". Recorded as a follow-up |
| Short silent walkthrough clips committed as plain files (ADR-0010) | Keep every video external, as the 2026-11-03 media plan said; Git LFS for MP4 files | The five clips are 1.5 to 3.4 MB each (10.4 MB together), under the 10 MB per file and 40 MB total ceiling the ADR sets; a file in the clone opens for any grader while an external link can expire. The narrated versions and video 1 stay external. LFS would add a dependency to every clone |
| No refresh tokens or revocation | Refresh endpoint plus a revocation list | SECURITY.md and ADR-0007 record the limitation: tokens expire after JWT_ACCESS_TOKEN_MINUTES, and get_current_user reloads the row so a deactivated user is rejected on the next request |
| MySQL default sql_mode written out in full, with ONLY_FULL_GROUP_BY | Leave the local server on its inherited mode, which had the flag off | CI runs mysql:8.4 with the default mode, so a query that only works with the flag off would pass locally and fail in CI. All 14 catalogue queries and the API and integration tests were run with the flag forced on before local_mysql.sh and docker-compose.yml were changed |
| The overdue check stays unscheduled | A cron entry or a scheduler thread in the API process | Scheduling is deployment configuration for a project that runs locally. The job is idempotent and reachable from make check-overdue and POST /analytics/alerts/checks/overdue-orders; docs/architecture/repository-structure.md states that nothing in the repository schedules it |
| Test database isolation by schema suffix and per-test TRUNCATE | Transaction rollback per test | backend/tests/conftest.py forces APP_ENV=test, which selects <MYSQL_DATABASE>_test, and refuses to run otherwise; migrations run once per session, every table is truncated before each test, reference data and demo users are re-applied. Rollback per test would hide the commit behaviour the API tests assert. Each parallel worktree used its own pair (fs_w01 to fs_w20 and their _test schemas) |
| The overdue endpoint ignores a body instead of rejecting it | Reject any body with 422 | Rejecting would have broken the frontend until 1140e0e landed; FastAPI ignores an undeclared body |

Assumptions and constraints: the demo scenario covers one production day on three machines; MySQL 8.4.0 is the only server version tested; the throttle state is per API process, so a multi-worker deployment would count failures per worker (a documented known discrepancy); timestamps are server local time without a zone.

## 4. AI help: what, why, accepted, revised, rejected, and verification

Tool: Claude Code (Anthropic). During the final wave it drafted the fixes, tests, and documentation changes on separate worktree branches, each gated by the full pytest suite against MySQL 8.4, ruff, mypy, ESLint, tsc, Vitest, and a production build before merge. Rows 29 to 43 of docs/ai_evidence/ai-use-record.md record the decisions, including two revisions (eight tests and the end-to-end helper rewritten for the pagination envelope; an unmigrated development database diagnosed from a 503 body) and one item left open (the 503 body for GET /health with MySQL stopped is still not asserted by an automated test).

[Write 100 to 150 words in your own voice: one suggestion from the final wave you accepted as drafted, one you changed and why, and one you rejected or deferred, each with the test, query, or EXPLAIN output you used to decide.]

## 5. Lessons learned at this milestone

- Parallel branches need a written contract before they start. The pagination envelope was decided on one branch while three sibling branches were written against bare arrays; eight API tests and the e2e helper failed at merge time (docs/ai_evidence/conversations/06-parallel-feature-integration.md).
- Run alembic upgrade head on every database after every merge. An unmigrated development database surfaced as "The database is not reachable" (503) because pymysql reports an unknown column (1054) as OperationalError; nothing in the code was wrong.
- MySQL drops the implicit index behind a foreign key when a composite index with the same leading column is created, but only when that index was auto-generated. Migration 6c1f0d2a9b47 handles both states so the upgrade is deterministic and the downgrade avoids error 1553.
- A local server can differ from CI in sql_mode. Writing the full MySQL 8.4 default into local_mysql.sh and docker-compose.yml removed the difference.
- A per-address login throttle behind a development proxy is a shared lock for everyone. The regression test uses two TestClient instances with different addresses so the behaviour is asserted, not assumed.
- [Add one lesson in your own words.]

## 6. Support or skill development needed for the next stage

[State any instructor support you need before the final presentation, for example a check of the Canvas submission format, or write "None at this time".]

[Name one skill you want to practice before the defense, for example reading EXPLAIN plans aloud or explaining the FOR UPDATE serialisation in alert_service.]

## 7. Next-step plan (final presentation and submission)

From the submission checklist in docs/milestones/README.md:

1. Merge feature/completion-integration to main, push, tag v1.0.0-rc1, and record the hash in the header of this report and of the Week 12 and 13 reports. [date]
2. Confirm the first GitHub Actions runs of all five workflows and record the run ids in docs/testing/test-matrix.md. Done 2026-11-08 (section 2).
3. Correct the stale README.md statements listed in section 2; rebuild the DOCX and PDF for Weeks 12, 13, and 14 with build_documents.py and check the page counts it prints. [date]
4. Replace every bracketed prompt in the three reports and in the six conversation records under docs/ai_evidence/conversations. [date]
5. Record the narration for videos 2 to 6 over the committed silent clips, prepare the slides for video 1, and add the links for the narrated versions to docs/media/videos/README.md. [date]
6. Upload Week14_Milestone_Report.pdf to Canvas before the scheduled lab defense; a repository commit does not replace the Canvas submission. [date]
7. During the defense, open the Canvas artifact and the repository; be ready to show make reset-demo, an investigation on CNC-03, the control chart with stepped limits, and the 429 and 422 error paths. [date]

## 8. Personal reflection (Shritej Gunda)

[Write 150 to 250 words in your own voice. Replace each prompt.]

[Which defect from the table in section 2 would you have shipped without the review, and what in your own testing habit let it through?]

[Explain the SELECT ... FOR UPDATE decision in the overdue check, or the per-subgroup control limits, in your own words as you would in the defense.]

[Describe one AI suggestion from the final wave that you revised or rejected, how you found the problem, and what you learned about MySQL or about testing from it.]

[What did running the whole suite against a real MySQL schema teach you that unit tests alone would not have?]

## 9. Personal-work summary

[List the artifacts you personally produced or verified for this milestone, one line each, with the file path or screen name: for example the migrations you ran up and down, the queries you checked under EXPLAIN, the README commands you executed, and the screenshots or video you recorded.]
