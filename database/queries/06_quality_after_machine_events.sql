-- Query 06: Quality change following machine events
-- Business question: For each fault or maintenance event on a machine, how did
--   the defect rate in the hours after the event compare with the hours before?
-- Tables: machine_events, inspections, production_units, production_batches
-- Techniques: LATERAL derived tables (MySQL 8.0.14+) evaluated per event row,
--   date arithmetic with INTERVAL, conditional aggregation, NULLIF
-- Parameters: :machine_id, :window_start, :window_end, :hours (comparison span)
-- Result: one row per non-state-change event with rate_before, rate_after,
--   and rate_change (after minus before). Both spans bound b.started_at so the
--   batch index can be range-scanned: a unit is inspected after its batch
--   starts, so the upper bounds lose nothing; the lower bound on the "before"
--   span means only batches started inside the lookback span are counted.
-- Used by: analytics endpoint (SQL explorer); rule R4 uses investigation/machine_events_before_onset.sql
-- Performance: EXPLAIN at demo volume with :machine_id = 3 and :hours = 3:
--   machine_events is a range scan on ix_machine_events_machine_time (3 rows,
--   Using index condition) and both lateral blocks are re-evaluated per event
--   (Rematerialize). Inside each block production_batches is read by ref on
--   the machine_id prefix of ix_production_batches_machine_time (11 rows,
--   covering index) and the started_at bounds are applied as "Using where" on
--   those index rows; MySQL does not range-scan on a bound taken from the
--   outer row, but the filter still drops batches outside the span before
--   units (ref on uq_unit_batch_sequence) and inspections (ref on
--   uq_inspection_unit_spec, time bounds as "Using where") are joined.
SELECT
    e.id          AS event_id,
    e.event_type,
    e.severity,
    e.description,
    e.occurred_at,
    before_stats.inspected AS inspected_before,
    before_stats.failed    AS failed_before,
    ROUND(before_stats.failed / NULLIF(before_stats.inspected, 0), 4) AS rate_before,
    after_stats.inspected  AS inspected_after,
    after_stats.failed     AS failed_after,
    ROUND(after_stats.failed / NULLIF(after_stats.inspected, 0), 4)   AS rate_after,
    ROUND(after_stats.failed / NULLIF(after_stats.inspected, 0)
          - before_stats.failed / NULLIF(before_stats.inspected, 0), 4) AS rate_change
FROM machine_events e
JOIN LATERAL (
    SELECT COUNT(i.id) AS inspected, COALESCE(SUM(i.result = 'FAIL'), 0) AS failed
    FROM production_batches b
    JOIN production_units   u ON u.batch_id = b.id
    JOIN inspections        i ON i.unit_id = u.id
    WHERE b.machine_id = e.machine_id
      AND b.started_at >= e.occurred_at - INTERVAL :hours HOUR
      AND b.started_at <  e.occurred_at
      AND i.inspected_at >= e.occurred_at - INTERVAL :hours HOUR
      AND i.inspected_at <  e.occurred_at
) AS before_stats
JOIN LATERAL (
    SELECT COUNT(i.id) AS inspected, COALESCE(SUM(i.result = 'FAIL'), 0) AS failed
    FROM production_batches b
    JOIN production_units   u ON u.batch_id = b.id
    JOIN inspections        i ON i.unit_id = u.id
    WHERE b.machine_id = e.machine_id
      AND b.started_at <  e.occurred_at + INTERVAL :hours HOUR
      AND i.inspected_at >= e.occurred_at
      AND i.inspected_at <  e.occurred_at + INTERVAL :hours HOUR
) AS after_stats
WHERE e.machine_id = :machine_id
  AND e.event_type <> 'STATE_CHANGE'
  AND e.occurred_at >= :window_start
  AND e.occurred_at <  :window_end
ORDER BY e.occurred_at;
