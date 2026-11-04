# Documented SQL queries

Factory Sherlock keeps its analytical SQL in files under `database/queries/`. The backend loads these files at startup (`backend/app/repositories/sql_loader.py`) and executes them with bound parameters (`backend/app/repositories/query_runner.py`), so the text below is the text that runs. Each file begins with a comment header stating its business question, tables, techniques, parameters, result shape, callers, and performance notes; `GET /analytics/queries` returns those headers as the SQL explorer catalogue.

This document explains each query and records real results obtained by running the files against the seeded demo database (MySQL 8.4.0, demo scenario from `database/seeds/demo_scenario.json`, seed 42). Parameter placeholders of the form `:name` were replaced by the literal values stated with each result. The database state when the results were captured (directly after `make reset-demo`, with no investigation opened): 9 orders, 35 batches, 700 units, 1,400 inspections, 51 failures, 12 machine events, and 2 alerts. Because no investigation exists, the `already_under_investigation` column of query 08 reads 0 on every row.

## Naming and loading

| File | Catalogue key | Loaded by |
|------|---------------|-----------|
| `01_machine_defect_rate_comparison.sql` | `machine_defect_rate_comparison` | dashboard, rule R1 |
| `02_production_performance.sql` | `production_performance` | dashboard |
| `03_recurring_defects.sql` | `recurring_defects` | dashboard, rule R2 |
| `04_material_lot_forward_trace.sql` | `material_lot_forward_trace` | `traceability_service.forward_trace` |
| `05_unit_backward_trace.sql` | `unit_backward_trace` | `traceability_service.backward_trace` |
| `06_quality_after_machine_events.sql` | `quality_after_machine_events` | dashboard |
| `07_order_completion_summary.sql` | `order_completion_summary` | dashboard |
| `08_batches_requiring_review.sql` | `batches_requiring_review` | dashboard, rule R5 |
| `09_daily_production_trend.sql` | `daily_production_trend` | dashboard |
| `investigation/defect_onset.sql` | `investigation.defect_onset` | rule R3 |
| `investigation/machine_events_before_onset.sql` | `investigation.machine_events_before_onset` | rule R4 |
| `investigation/shared_material_lots.sql` | `investigation.shared_material_lots` | rule R6 |

"Dashboard" means `analytics_service.DASHBOARD_QUERIES`, served by `GET /analytics/queries/{name}` with `window_start`, `window_end`, `machine_id`, `threshold`, `hours`, and `limit` query parameters (defaults: a 30-day window ending tomorrow, threshold 0.10, hours 3, limit 50). The rules are in `backend/app/investigation/rules.py`. Investigation rules use `RuleThresholds` defaults: batch review rate 0.10, event lookback 6 hours, event comparison 3 hours.

All time windows are half-open: `>= :window_start AND < :window_end`.

## Query 01: Machine defect-rate comparison

**Business question.** Which machines produced the highest share of failed inspections in a window, and how does each compare with the fleet?

**Tables.** machines, production_batches, production_units, inspections.

**Techniques.** CTE (`window_inspections`) that applies the time filter to `inspections` first, joins up to units and batches, and aggregates per `machine_id`; `machines` is then `LEFT JOIN`ed to that result so a machine with no inspections still appears with `inspected = 0` and a NULL `defect_rate` that ranks last; conditional aggregation `SUM(i.result = 'FAIL')` (a boolean expression summed as 0 or 1); window functions `SUM(...) OVER ()` for the fleet totals and `RANK() OVER (ORDER BY ...)` for the position; `NULLIF(inspected, 0)` to avoid division by zero.

**Parameters.** `:window_start`, `:window_end`.

**Result.** One row per machine: `machine_id`, `machine_code`, `machine_name`, `inspected`, `failed`, `defect_rate`, `fleet_defect_rate`, `defect_rank` (1 = worst), ordered by rank.

**Used by.** Dashboard; rule R1, which reads the row for the investigated machine, sets `ctx.elevated` when the rate is at least 0.05 and at least twice the fleet rate, and stores the full result as evidence.

**Result captured** with `:window_start = '2026-11-01 00:00:00'`, `:window_end = '2026-11-05 00:00:00'`:

| machine_id | machine_code | machine_name | inspected | failed | defect_rate | fleet_defect_rate | defect_rank |
|-----------:|--------------|--------------|----------:|-------:|------------:|------------------:|------------:|
| 3 | CNC-03 | CNC Machine 03 | 480 | 46 | 0.0958 | 0.0364 | 1 |
| 2 | CNC-02 | CNC Machine 02 | 440 | 3 | 0.0068 | 0.0364 | 2 |
| 1 | CNC-01 | CNC Machine 01 | 480 | 2 | 0.0042 | 0.0364 | 3 |

CNC-02 has 440 inspections rather than 480 because it lost one batch slot to simulated downtime.

**Performance.** `EXPLAIN` at demo volume (all 1,400 inspections inside the four-day window): the derived table is driven from `production_batches` with an index scan of `ix_production_batches_machine_time` (35 rows, Using index), units by `ref` on `uq_unit_batch_sequence` (Using index), and inspections by `ref` on `uq_inspection_unit_spec` with the time filter applied as `Using where`; `ix_inspections_time_result` is in `possible_keys` but not chosen. With a one-hour window (`2026-11-02 10:00` to `11:00`) the derived table becomes a `range` scan on `ix_inspections_time_result` (240 rows, Using index condition) followed by `eq_ref` lookups to units and batches. `machines` (3 rows, `ALL`) is joined to the grouped rows through the derived table's `<auto_key0>`, and one filesort orders the three result rows.

## Query 02: Production order performance

**Business question.** For each order, how far along is it, how long did production take, and is it on time, late, or overdue?

**Tables.** production_orders, products, machines, production_batches.

**Techniques.** Four-table join with `LEFT JOIN` for the optional machine and for orders with no batches; aggregation `COUNT`, `MIN`, `MAX`; `TIMESTAMPDIFF(MINUTE, ...)`; `CASE` for `schedule_status`; `CURDATE()` comparison for overdue orders; parameterised `LIMIT`.

**Parameters.** `:limit`.

**Result.** One row per order, newest first: identifiers, status, planned and completed quantities, `completion_pct`, `batch_count`, first batch start, last batch completion, `production_minutes`, `due_date`, `schedule_status`: `ON_TIME` or `LATE` for a completed order with a due date and at least one completed batch, `OVERDUE` for an open order past its due date, and `NOT_APPLICABLE` when there is no due date or when a completed order has no completed batch to date it by (an order completed through a status change rather than through batches would otherwise have read `LATE`).

**Used by.** Dashboard.

**Result captured** with `:limit = 10` on 2026-11-03 (the `OVERDUE` label depends on `CURDATE()`):

| order_id | order_number | product_name | machine_code | status | quantity_planned | quantity_completed | completion_pct | batch_count | first_batch_started | last_batch_completed | production_minutes | due_date | schedule_status |
|---------:|--------------|--------------|--------------|--------|-----------------:|-------------------:|---------------:|------------:|---------------------|----------------------|-------------------:|----------|-----------------|
| 9 | SIM0001-CNC-03-03 | Steel shaft 20 mm | CNC-03 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 10:00:00 | 2026-11-02 12:00:00 | 120 | 2026-11-02 | ON_TIME |
| 6 | SIM0001-CNC-02-03 | Metal bracket | CNC-02 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 10:00:00 | 2026-11-02 12:00:00 | 120 | 2026-11-02 | ON_TIME |
| 3 | SIM0001-CNC-01-03 | Spur gear 60 mm | CNC-01 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 10:00:00 | 2026-11-02 12:00:00 | 120 | 2026-11-02 | ON_TIME |
| 8 | SIM0001-CNC-03-02 | Steel shaft 20 mm | CNC-03 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 08:00:00 | 2026-11-02 10:00:00 | 120 | 2026-11-02 | ON_TIME |
| 5 | SIM0001-CNC-02-02 | Metal bracket | CNC-02 | IN_PROGRESS | 80 | 60 | 75.0 | 3 | 2026-11-02 08:00:00 | 2026-11-02 10:00:00 | 120 | 2026-11-02 | OVERDUE |
| 2 | SIM0001-CNC-01-02 | Spur gear 60 mm | CNC-01 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 08:00:00 | 2026-11-02 10:00:00 | 120 | 2026-11-02 | ON_TIME |
| 7 | SIM0001-CNC-03-01 | Steel shaft 20 mm | CNC-03 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 06:00:00 | 2026-11-02 08:00:00 | 120 | 2026-11-02 | ON_TIME |
| 4 | SIM0001-CNC-02-01 | Metal bracket | CNC-02 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 06:00:00 | 2026-11-02 08:00:00 | 120 | 2026-11-02 | ON_TIME |
| 1 | SIM0001-CNC-01-01 | Spur gear 60 mm | CNC-01 | COMPLETED | 80 | 80 | 100.0 | 4 | 2026-11-02 06:00:00 | 2026-11-02 08:00:00 | 120 | 2026-11-02 | ON_TIME |

Nine rows were returned because the demo contains nine orders. Order 5 shows the batch lost to downtime: three batches, 60 of 80 units, still `IN_PROGRESS`, and `OVERDUE` because its due date has passed.

**Performance.** `ix_production_batches_order` supports the batch aggregation per order; the `ORDER BY o.created_at DESC` is a filesort over a small table. Orders sharing the same `created_at` (the simulation gives the three orders that start together the same time) are returned in an order MySQL chooses among ties.

## Query 03: Recurring defect categories by machine

**Business question.** Which defect categories recur on each machine in a window, and what share of that machine's defects does each represent?

**Tables.** inspection_defects, inspections, defect_types, production_units, production_batches, machines.

**Techniques.** CTE; a six-table join that traverses two bridge tables (`inspection_defects` and the unit-to-batch chain); window functions with `PARTITION BY machine_code` (`SUM OVER` for the machine total, `DENSE_RANK OVER` for rank within machine); the optional-parameter pattern `(:machine_id IS NULL OR m.id = :machine_id)` so one statement serves both "one machine" and "all machines".

**Parameters.** `:window_start`, `:window_end`, `:machine_id` (NULL for all machines).

**Result.** One row per (machine, defect type): `occurrences`, `machine_total`, `share_of_machine_defects`, `rank_within_machine`.

**Used by.** Dashboard; rule R2 takes the first row (the dominant defect on the investigated machine).

**Result captured** with the window above and `:machine_id = 3`:

| machine_id | machine_code | defect_code | defect_name | occurrences | machine_total | share_of_machine_defects | rank_within_machine |
|-----------:|--------------|-------------|-------------|------------:|--------------:|-------------------------:|--------------------:|
| 3 | CNC-03 | OVERSIZE_DIAMETER | Oversized diameter | 45 | 46 | 0.9783 | 1 |
| 3 | CNC-03 | DIMENSIONAL_DEVIATION | Dimensional deviation | 1 | 46 | 0.0217 | 2 |

With `:machine_id = NULL` the same statement returned four rows: CNC-01 with 2 `OVERSIZE_DIAMETER`, CNC-02 with 3 `HOLE_POSITION_DEVIATION`, and the two CNC-03 rows above.

**Performance.** With `:machine_id = 3`, `EXPLAIN` shows `machines` resolved as `const`; `inspection_defects` read with an index scan of its `defect_type_id` index (`index`, Using index, 51 rows); and `defect_types`, `inspections`, `production_units`, and `production_batches` each reached by `eq_ref` on its primary key, with the time window applied as `Using where` on `inspections` and the machine filter as `Using where` on `production_batches` (filtered 34%). `ix_inspections_time_result` is in `possible_keys` but not used. One temporary table for the `GROUP BY` and one filesort for the window ordering over the small CTE output.

## Query 04: Material lot forward traceability

**Business question.** Given a material lot, which batches consumed it, on which machines and orders, and how many of the resulting units failed inspection?

**Tables.** material_lots, batch_materials, production_batches, machines, production_orders, products, production_units, inspections.

**Techniques.** Many-to-many traversal through `batch_materials`; eight-table join; `COUNT(DISTINCT u.id)` so units are not multiplied by their inspections; `COUNT(DISTINCT CASE WHEN i.result = 'FAIL' THEN i.unit_id END)` to count a unit once even if several of its inspections failed; `LEFT JOIN` so a batch with no units or inspections still appears.

**Parameters.** `:lot_number`.

**Result.** One row per batch that used the lot, ordered by `started_at`.

**Used by.** `GET /traceability/forward/{lot_number}` through `traceability_service.forward_trace`, which first checks that the lot exists so an unknown lot returns 404 rather than an empty list.

**Result captured** with `:lot_number = 'L201'`:

| lot_number | material_name | supplier | lot_status | batch_id | batch_number | batch_status | started_at | machine_code | order_number | product_name | quantity_used | units_produced | units_failed |
|------------|---------------|----------|------------|---------:|--------------|--------------|------------|--------------|--------------|--------------|--------------:|---------------:|-------------:|
| L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 24 | SIM0001-CNC-03-01-B01 | COMPLETED | 2026-11-02 06:00:00 | CNC-03 | SIM0001-CNC-03-01 | Steel shaft 20 mm | 20.00 | 20 | 0 |
| L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 25 | SIM0001-CNC-03-01-B02 | COMPLETED | 2026-11-02 06:30:00 | CNC-03 | SIM0001-CNC-03-01 | Steel shaft 20 mm | 20.00 | 20 | 0 |
| L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 29 | SIM0001-CNC-03-02-B02 | COMPLETED | 2026-11-02 08:30:00 | CNC-03 | SIM0001-CNC-03-02 | Steel shaft 20 mm | 20.00 | 20 | 0 |
| L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 30 | SIM0001-CNC-03-02-B03 | COMPLETED | 2026-11-02 09:00:00 | CNC-03 | SIM0001-CNC-03-02 | Steel shaft 20 mm | 20.00 | 20 | 1 |
| L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 31 | SIM0001-CNC-03-02-B04 | COMPLETED | 2026-11-02 09:30:00 | CNC-03 | SIM0001-CNC-03-02 | Steel shaft 20 mm | 20.00 | 20 | 0 |
| L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 35 | SIM0001-CNC-03-03-B04 | COMPLETED | 2026-11-02 11:30:00 | CNC-03 | SIM0001-CNC-03-03 | Steel shaft 20 mm | 20.00 | 20 | 18 |

The last row shows the batch at the end of the tool-wear fault: 18 of 20 units failed. The lot is used only on CNC-03 because the simulation assigns lots to products and each machine makes one product.

**Performance.** `EXPLAIN`: `material_lots` resolved as `const` through the unique `lot_number` key; `batch_materials` read by its implicit `material_lot_id` index (6 rows); batches, orders, and products by primary key (`eq_ref`); units through `uq_unit_batch_sequence` and inspections through `uq_inspection_unit_spec`. The optimizer joined `machines` (3 rows) with a hash join. One temporary table and filesort for the `GROUP BY` and `ORDER BY`.

## Query 05: Unit backward traceability

**Business question.** Given a serial number, which batch, machine, order, product, and material lots does the unit come from, and what did inspection find?

**Tables.** production_units, production_batches, machines, production_orders, products, batch_materials, material_lots, inspections, product_specifications.

**Techniques.** Join chain from child to ancestors; `LEFT JOIN` to lots so a batch without recorded materials still traces; a correlated scalar subquery using `GROUP_CONCAT(... ORDER BY ... SEPARATOR '; ')` to fold all of the unit's inspection results into one column.

**Parameters.** `:serial_number`.

**Result.** One row per material lot used by the unit's batch; the unit, batch, machine, order, and product columns repeat on each row. `inspection_summary` lists each characteristic with its measured value and result. Known limit: it is a `GROUP_CONCAT`, so it is cut at `group_concat_max_len` (1024 characters by default), which would matter only for a unit with roughly 25 or more characteristics.

**Used by.** `GET /traceability/backward/{serial_number}` through `traceability_service.backward_trace`, which raises 404 when no rows return.

**Result captured** with `:serial_number = 'SIM0001-CNC-03-02-B03-U0014'` (chosen with `SELECT` as the earliest failing unit on CNC-03):

| serial_number | produced_at | batch_number | batch_status | machine_code | machine_name | order_number | product_code | product_name | lot_number | material_name | supplier | lot_status | inspection_summary |
|---------------|-------------|--------------|--------------|--------------|--------------|--------------|--------------|--------------|------------|---------------|----------|------------|--------------------|
| SIM0001-CNC-03-02-B03-U0014 | 2026-11-02 09:21:00 | SIM0001-CNC-03-02-B03 | COMPLETED | CNC-03 | CNC Machine 03 | SIM0001-CNC-03-02 | STEEL-SHAFT | Steel shaft 20 mm | L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | diameter=20.101 FAIL; length=149.842 PASS |

The diameter of 20.101 mm is 0.001 mm beyond the 0.100 mm tolerance on the 20.000 mm target: the first unit to fail under the tool-wear drift.

**Performance.** `EXPLAIN`: the unit, batch, machine, order, and product are all `const` (resolved through `serial_number` and primary keys before the join runs); `batch_materials` is read by primary key prefix; the `GROUP_CONCAT` subquery is a `DEPENDENT SUBQUERY` on `uq_inspection_unit_spec` (2 rows per unit) that runs once per output row.

## Query 06: Quality change following machine events

**Business question.** For each fault or maintenance event on a machine, how did the defect rate in the hours after the event compare with the hours before?

**Tables.** machine_events, inspections, production_units, production_batches.

**Techniques.** Two `JOIN LATERAL` derived tables (MySQL 8.0.14 and later), each evaluated once per event row and allowed to reference `e.machine_id` and `e.occurred_at`; `INTERVAL :hours HOUR` arithmetic; conditional aggregation; `NULLIF` guards; a computed `rate_change`. Each block also bounds `b.started_at`: a unit is inspected after its batch starts, so the upper bounds (`started_at < occurred_at` before, `started_at < occurred_at + :hours` after) exclude nothing, and the lower bound on the before span means only batches started inside the lookback span are counted.

**Parameters.** `:machine_id`, `:window_start`, `:window_end`, `:hours`.

**Result.** One row per non-state-change event in the window: event details, inspected and failed counts before and after, `rate_before`, `rate_after`, `rate_change`.

**Used by.** The analytics endpoint (SQL explorer and dashboard) only. Rule R4 uses `investigation/machine_events_before_onset.sql` instead.

**Result captured** with `:machine_id = 3`, the window above, `:hours = 3`:

| event_id | event_type | severity | description | occurred_at | inspected_before | failed_before | rate_before | inspected_after | failed_after | rate_after | rate_change |
|---------:|------------|----------|-------------|-------------|-----------------:|--------------:|------------:|----------------:|-------------:|-----------:|------------:|
| 12 | TOOL_WEAR | WARNING | Simulated cutting tool wear: dimensions drift upward over time | 2026-11-02 08:00:00 | 158 | 0 | 0.0000 | 240 | 14 | 0.0583 | 0.0583 |

Only 158 inspections fall in the three hours before 08:00 because production started at 06:00 and the half-open interval excludes the units inspected exactly at 08:00.

**Performance.** `EXPLAIN` with `:machine_id = 3` and `:hours = 3` shows `machine_events` read as a `range` on `ix_machine_events_machine_time` (3 rows, Using index condition) with `Rematerialize (<derived2>,<derived3>)`, which is how MySQL reports lateral derived tables being re-evaluated per outer row. Inside each block `production_batches` is read by `ref` on the `machine_id` prefix of `ix_production_batches_machine_time` (11 rows, Using where; Using index): MySQL does not range-scan on a bound taken from the outer row, so the `started_at` bounds are applied as a filter on the covering index rows, which still drops batches outside the span before units (`ref` on `uq_unit_batch_sequence`) and inspections (`ref` on `uq_inspection_unit_spec`, time bounds as `Using where`) are joined.

## Query 07: Production order completion summary

**Business question.** How many orders and units are planned versus completed, by product and status, with subtotals and a grand total?

**Tables.** production_orders, products.

**Techniques.** `GROUP BY p.code, o.status WITH ROLLUP`, grouping by the unique product code so two products that share a display name cannot merge, with `MAX(p.name)` carrying the name (constant within a code group); `GROUPING()` to distinguish a subtotal row (where the column is NULL because it was rolled up) from a genuine NULL, rendering the label `ALL` in `product_code`, `product_name`, and `status`; `NULLIF`-guarded percentage.

**Parameters.** None.

**Result.** One row per (product, status), one subtotal per product, and one grand total.

**Used by.** Dashboard.

**Result captured:**

| product_code | product_name | status | orders | planned_units | completed_units | completion_pct |
|--------------|--------------|--------|-------:|--------------:|----------------:|---------------:|
| GEAR | Spur gear 60 mm | COMPLETED | 3 | 240 | 240 | 100.0 |
| GEAR | Spur gear 60 mm | ALL | 3 | 240 | 240 | 100.0 |
| METAL-BRACKET | Metal bracket | COMPLETED | 2 | 160 | 160 | 100.0 |
| METAL-BRACKET | Metal bracket | IN_PROGRESS | 1 | 80 | 60 | 75.0 |
| METAL-BRACKET | Metal bracket | ALL | 3 | 240 | 220 | 91.7 |
| STEEL-SHAFT | Steel shaft 20 mm | COMPLETED | 3 | 240 | 240 | 100.0 |
| STEEL-SHAFT | Steel shaft 20 mm | ALL | 3 | 240 | 240 | 100.0 |
| ALL | ALL | ALL | 9 | 720 | 700 | 97.2 |

Rows are ordered by product code because that is the grouping column.

**Performance.** A single pass over `production_orders` (9 rows) joined to `products` by primary key. `ix_production_orders_status` is not needed because every row is aggregated.

## Query 08: Batches requiring quality review

**Business question.** Which batches in a window have a defect rate at or above a threshold, are not already quarantined, and are they already attached to an investigation?

**Tables.** production_batches, machines, production_orders, products, production_units, inspections, investigation_batches.

**Techniques.** CTE computing per-batch counts; the threshold filter applied in the outer query to the unrounded ratio `failed / NULLIF(inspected, 0)` (the same effect as `HAVING`), while the `defect_rate` column in the output is rounded to four places for display, so a batch at 0.09996 is not rounded up to 0.1000 and wrongly flagged; correlated `EXISTS` against `investigation_batches`; optional machine filter.

**Parameters.** `:window_start`, `:window_end`, `:threshold` (0.0 to 1.0), `:machine_id` (NULL for all).

**Result.** One row per batch at or above the threshold, worst first, with `already_under_investigation` as 0 or 1.

**Used by.** Dashboard; rule R5, which stores the batch ids on the context so rule R6 can look up shared lots and so the service can insert `investigation_batches` rows.

**Result captured** with the window above, `:threshold = 0.10`, `:machine_id = NULL`:

| batch_id | batch_number | batch_status | machine_code | product_name | started_at | inspected | failed | defect_rate | already_under_investigation |
|---------:|--------------|--------------|--------------|--------------|------------|----------:|-------:|------------:|----------------------------:|
| 35 | SIM0001-CNC-03-03-B04 | COMPLETED | CNC-03 | Steel shaft 20 mm | 2026-11-02 11:30:00 | 40 | 19 | 0.4750 | 0 |
| 34 | SIM0001-CNC-03-03-B03 | COMPLETED | CNC-03 | Steel shaft 20 mm | 2026-11-02 11:00:00 | 40 | 12 | 0.3000 | 0 |
| 33 | SIM0001-CNC-03-03-B02 | COMPLETED | CNC-03 | Steel shaft 20 mm | 2026-11-02 10:30:00 | 40 | 10 | 0.2500 | 0 |
| 32 | SIM0001-CNC-03-03-B01 | COMPLETED | CNC-03 | Steel shaft 20 mm | 2026-11-02 10:00:00 | 40 | 4 | 0.1000 | 0 |

`already_under_investigation` is 0 on every row because the results were captured on a freshly reset database. After an investigation scoped to CNC-03 is opened through the API, `investigation_batches` holds exactly these four batch ids with reason "Defect rate above review threshold" and the column reads 1. Batch 32 is included because its unrounded ratio, 4/40, is exactly the threshold.

**Performance.** `EXPLAIN` with `:machine_id = NULL` shows a full scan of `production_batches` (`ALL`, 35 rows) with `ix_production_batches_machine_time` in `possible_keys` but unused: the `(:machine_id IS NULL OR ...)` pattern prevents a range scan, and at 35 rows a scan is cheaper anyway. `machines`, `production_orders`, and `products` are `eq_ref` on their primary keys, units are `ref` on `uq_unit_batch_sequence`, and inspections `ref` on `uq_inspection_unit_spec`; one temporary table for the `GROUP BY` and a filesort for the final `ORDER BY`. The `EXISTS` probe is a `DEPENDENT SUBQUERY` using the implicit `batch_id` index on `investigation_batches`.

## Query 09: Daily production trend by machine

**Business question.** How many units did each machine produce per day, and how many of them failed at least one inspection?

**Tables.** production_units, production_batches, machines, inspections.

**Techniques.** `DATE()` bucketing; `COUNT(DISTINCT u.id)`; `COUNT(DISTINCT CASE WHEN i.result = 'FAIL' THEN u.id END)` so a unit with two failed inspections is counted once; `LEFT JOIN` to inspections so uninspected units still count as produced.

**Parameters.** `:window_start`, `:window_end`.

**Result.** One row per (day, machine).

**Used by.** Dashboard.

**Result captured** with the window above:

| production_date | machine_code | units_produced | units_failed |
|-----------------|--------------|---------------:|-------------:|
| 2026-11-02 | CNC-01 | 240 | 2 |
| 2026-11-02 | CNC-02 | 220 | 3 |
| 2026-11-02 | CNC-03 | 240 | 45 |

CNC-03 shows 45 failed units for 46 failed inspections: one unit failed both of its characteristics.

**Performance.** `EXPLAIN` at demo volume (all 700 units inside the four-day window) starts from `machines` (index scan on `code`, 3 rows, Using temporary; Using filesort), reaches batches by `ref` on `ix_production_batches_machine_time`, units by `ref` on `uq_unit_batch_sequence` with the `produced_at` filter as `Using where`, and inspections by `ref` on `uq_inspection_unit_spec`. `ix_production_units_produced_at` is in `possible_keys` but not chosen when every unit is inside the window; with a one-hour window (`2026-11-02 10:00` to `11:00`) `EXPLAIN` shows a `range` scan on that index (120 rows, Using index) followed by `eq_ref` lookups to batches and machines. See [database-design.md](database-design.md), section 6.

## Investigation query: defect_onset

**Business question.** When did a machine's defect rate start to rise?

**Tables.** inspections, production_units, production_batches.

**Techniques.** CTE; `DATE_FORMAT(i.inspected_at, '%Y-%m-%dT%H:00:00')` to bucket by hour (an ISO 8601 string with a `T` separator, which `datetime.fromisoformat` parses in rule R3); `LAG(...) OVER (ORDER BY bucket_start)` for the rate of the previous non-empty bucket (an hour with no inspections produces no row, so this is the previous clock hour only while production was continuous); cumulative `SUM(...) OVER (ORDER BY bucket_start)` for the running rate.

**Parameters.** `:machine_id`, `:window_start`, `:window_end`.

**Result.** One row per hour bucket: `inspected`, `failed`, `defect_rate`, `previous_bucket_rate`, `cumulative_rate`.

**Used by.** Rule R3, which picks the first bucket whose `defect_rate` is at or above the batch review threshold (0.10) and sets `ctx.onset_time` to its `bucket_start`.

**Result captured** with `:machine_id = 3` and the window above:

| bucket_start | inspected | failed | defect_rate | previous_bucket_rate | cumulative_rate |
|--------------|----------:|-------:|------------:|---------------------:|----------------:|
| 2026-11-02T06:00:00 | 78 | 0 | 0.0000 | NULL | 0.0000 |
| 2026-11-02T07:00:00 | 80 | 0 | 0.0000 | 0.0000 | 0.0000 |
| 2026-11-02T08:00:00 | 80 | 0 | 0.0000 | 0.0000 | 0.0000 |
| 2026-11-02T09:00:00 | 80 | 1 | 0.0125 | 0.0000 | 0.0031 |
| 2026-11-02T10:00:00 | 80 | 13 | 0.1625 | 0.0125 | 0.0352 |
| 2026-11-02T11:00:00 | 80 | 31 | 0.3875 | 0.1625 | 0.0941 |
| 2026-11-02T12:00:00 | 2 | 1 | 0.5000 | 0.3875 | 0.0958 |

The onset bucket under the default threshold is 10:00, two hours after the tool-wear event at 08:00. The final bucket holds only the two inspections stamped exactly 12:00:00.

**Performance.** `EXPLAIN`: batches by `ix_production_batches_machine_time` (`ref`, const machine id), units by `uq_unit_batch_sequence`, inspections by `uq_inspection_unit_spec` with the time filter as `Using where`; one temporary table for the `GROUP BY` and a filesort for the window ordering.

## Investigation query: machine_events_before_onset

**Business question.** What happened to the machine in the hours before the defect rate started to rise?

**Tables.** machine_events.

**Techniques.** Range scan on the composite index `(machine_id, occurred_at)`; `INTERVAL :lookback_hours HOUR`; `TIMESTAMPDIFF(MINUTE, ...)`; exclusion of `STATE_CHANGE` rows so only faults and maintenance are listed.

**Parameters.** `:machine_id`, `:onset_time`, `:lookback_hours`.

**Result.** Events ordered most recent first with `minutes_before_onset`.

**Used by.** Rule R4, which runs only when R3 found an onset. Its narrative states that timing suggests a relationship and does not claim causation.

**Result captured** with `:machine_id = 3`, `:onset_time = '2026-11-02 10:00:00'` (from `defect_onset` above), `:lookback_hours = 6`:

| event_id | event_type | severity | description | occurred_at | minutes_before_onset |
|---------:|------------|----------|-------------|-------------|---------------------:|
| 12 | TOOL_WEAR | WARNING | Simulated cutting tool wear: dimensions drift upward over time | 2026-11-02 08:00:00 | 120 |

**Performance.** `EXPLAIN`: single `range` access on `ix_machine_events_machine_time` with `Using index condition` and `Backward index scan`, which serves the `ORDER BY occurred_at DESC` without a filesort.

## Investigation query: shared_material_lots

**Business question.** Do the affected batches share a material lot, and how widely was that lot used elsewhere?

**Tables.** material_lots, batch_materials, production_batches.

**Techniques.** Expanding `IN :batch_ids` parameter (declared with `bindparam(expanding=True)` in `sql_loader.load_query`, which is why `query_runner.EXPANDING_PARAMS` lists this query); `COUNT(DISTINCT bm.batch_id)`; `GROUP_CONCAT(DISTINCT ... ORDER BY ...)`; a correlated scalar subquery for the lot's total usage across all batches.

**Parameters.** `:batch_ids` (list of batch ids).

**Result.** One row per lot used by any of the given batches; `affected_batches_using_lot > 1` means the lot is shared among the flagged batches. Known limit: `batch_numbers` is a `GROUP_CONCAT` and is cut at `group_concat_max_len` (1024 characters by default, about 40 batch numbers); the counts stay exact.

**Used by.** Rule R6, which runs only when R5 found affected batches.

**Result captured** with `:batch_ids = (32, 33, 34, 35)` (the batch ids returned by query 08):

| lot_id | lot_number | material_name | supplier | lot_status | affected_batches_using_lot | batch_numbers | total_batches_using_lot |
|-------:|------------|---------------|----------|------------|---------------------------:|---------------|------------------------:|
| 3 | L203 | Steel bar stock 4140 | Harbor Metals | AVAILABLE | 3 | SIM0001-CNC-03-03-B01, SIM0001-CNC-03-03-B03, SIM0001-CNC-03-03-B04 | 6 |
| 2 | L202 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 2 | SIM0001-CNC-03-03-B01, SIM0001-CNC-03-03-B02 | 4 |
| 1 | L201 | Steel bar stock 4140 | Northline Steel | AVAILABLE | 1 | SIM0001-CNC-03-03-B04 | 6 |

Lots L203 and L202 are shared among the flagged batches, but L203 was also used by three batches that were not flagged, and the dominant defect is oversize diameter following a tool-wear event; the engineer, not the query, decides what that means.

**Performance.** `EXPLAIN`: `production_batches` as a `range` on the primary key for the `IN` list (4 rows), `batch_materials` by primary key prefix (Using index), lots by primary key; the total-usage subquery is a `DEPENDENT SUBQUERY` on the implicit `material_lot_id` index.

## Reproducing the results

Replace the placeholders with literals and pipe the file to the `mysql` client, for example:

```sh
sed -e "s/:window_start/'2026-11-01 00:00:00'/g" \
    -e "s/:window_end/'2026-11-05 00:00:00'/g" \
    database/queries/01_machine_defect_rate_comparison.sql \
  | mysql --no-defaults -h127.0.0.1 -P3307 -usherlock_app -p factory_sherlock
```

Prefix the statement with `EXPLAIN` to obtain the plans quoted above. Through the API, `GET /analytics/queries/machine_defect_rate_comparison?window_start=2026-11-01T00:00:00&window_end=2026-11-05T00:00:00` returns the same rows together with the SQL text and the bound parameters.
