-- Query 09: Daily production trend by machine
-- Business question: How many units did each machine produce per day, and how
--   many of them failed at least one inspection?
-- Tables: production_units, production_batches, machines, inspections
-- Techniques: DATE() bucketing, COUNT(DISTINCT) with CASE to count a unit once
--   even when it has several failed inspections
-- Parameters: :window_start, :window_end
-- Result: one row per (day, machine)
-- Used by: analytics dashboard (daily trend chart)
-- Performance: EXPLAIN at demo volume (700 units, all inside the four-day
--   window) starts from machines (index scan on code, 3 rows), reaches batches
--   by ref on ix_production_batches_machine_time, units by ref on
--   uq_unit_batch_sequence with the produced_at filter as "Using where", and
--   inspections by ref on uq_inspection_unit_spec; one temporary table and a
--   filesort for the GROUP BY. ix_production_units_produced_at is in
--   possible_keys but not chosen when every unit is inside the window; with a
--   one-hour window EXPLAIN shows a range scan on that index (120 rows, Using
--   index) followed by eq_ref lookups to batches and machines.
SELECT
    DATE(u.produced_at) AS production_date,
    m.code              AS machine_code,
    COUNT(DISTINCT u.id) AS units_produced,
    COUNT(DISTINCT CASE WHEN i.result = 'FAIL' THEN u.id END) AS units_failed
FROM production_units u
JOIN production_batches b ON b.id = u.batch_id
JOIN machines           m ON m.id = b.machine_id
LEFT JOIN inspections   i ON i.unit_id = u.id
WHERE u.produced_at >= :window_start
  AND u.produced_at <  :window_end
GROUP BY production_date, m.code
ORDER BY production_date, m.code;
